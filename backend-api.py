import os
import hashlib
import re
import threading
import time
import json
import csv
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from unicodedata import normalize as unicode_normalize
import difflib

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Request, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pdf2image import convert_from_path
from PIL import Image
from chandra.model import InferenceManager
from chandra.model.schema import BatchInputItem
from sentence_transformers import SentenceTransformer
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# ==================== CONFIG ====================
MAX_FILE_SIZE = 500 * 1024 * 1024
UPLOAD_DIR = Path("./uploaded_files")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path("./ocr_output")
OUTPUT_DIR.mkdir(exist_ok=True)

DPI = 300
MAX_PAGES = None
MAX_WORKERS = 2
BATCH_SIZE = 16
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = "keepitreal/vietnamese-sbert"
LLM_MODEL = "vilm/vietcuna-7b-v3"
MAX_NEW_TOKENS = 2048
TEMPERATURE = 0.1

documents_storage = {}
ocr_results_cache = {}
ocr_global_lock = threading.Lock()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, document_id: str):
        await websocket.accept()
        if document_id not in self.active_connections:
            self.active_connections[document_id] = []
        self.active_connections[document_id].append(websocket)
        print(f"✅ WebSocket connected for document: {document_id}")

    def disconnect(self, websocket: WebSocket, document_id: str):
        if document_id in self.active_connections:
            self.active_connections[document_id].remove(websocket)
            if not self.active_connections[document_id]:
                del self.active_connections[document_id]
        print(f"❌ WebSocket disconnected for document: {document_id}")

    async def send_completion(self, document_id: str, data: dict):
        if document_id in self.active_connections:
            for connection in self.active_connections[document_id]:
                try:
                    await connection.send_json(data)
                    print(f"📤 Sent completion notification to client for {document_id}")
                except Exception as e:
                    print(f"❌ Error sending to WebSocket: {e}")

manager = ConnectionManager()

# ==================== UTILITIES ====================

def normalize_text(text):
    text = unicode_normalize('NFKC', text).upper()
    replacements = {'HOÀ': 'HÒA', 'HOẠ': 'HÒA'}
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r'\s+', ' ', text).strip()

def fuzzy_contains(haystack, needle, threshold=0.75):
    haystack_norm = normalize_text(haystack)
    needle_norm = normalize_text(needle)

    if needle_norm in haystack_norm:
        return True, 1.0

    best_ratio = 0.0
    needle_len = len(needle_norm)

    for i in range(len(haystack_norm) - needle_len + 1):
        substring = haystack_norm[i:i + needle_len]
        ratio = difflib.SequenceMatcher(None, substring, needle_norm).ratio()
        best_ratio = max(best_ratio, ratio)
        if best_ratio >= threshold:
            return True, best_ratio

    return best_ratio >= threshold, best_ratio

def clean_text(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\|[\s\-:]+\|', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_markdown(md_text):
    elements = {
        "headings": [],
        "paragraphs": [],
        "lists": [],
        "tables": [],
        "key_value_pairs": []
    }

    lines = md_text.split('\n')
    current_list = []
    current_table = []
    in_table = False

    for line in lines:
        s = line.strip()

        if not s:
            continue

        if s.startswith('#'):
            if s.startswith('####'):
                heading_text = s[4:].strip()
                level = 4
            elif s.startswith('###'):
                heading_text = s[3:].strip()
                level = 3
            elif s.startswith('##'):
                heading_text = s[2:].strip()
                level = 2
            else:
                heading_text = s[1:].strip()
                level = 1

            if heading_text:
                elements["headings"].append({"level": level, "text": heading_text})
            continue

        text_only = re.sub(r'[0-9\s\.\,\-\:\;\(\)\[\]\/\\\"\'\`\|\–\—]', '', s)

        is_uppercase = text_only and text_only == text_only.upper()
        is_short = len(s) <= 100
        is_not_empty = len(text_only) > 0
        is_not_date = not re.search(r'ngày|tháng|năm|\d{1,2}/\d{1,2}/\d{4}', s, re.IGNORECASE)
        is_not_location = not re.search(r'^(Hà Nội|TP\.|Thành phố)', s)
        is_not_signature = not re.search(r'(Thiếu tướng|Đại tá|Trung tá)', s)

        if (is_uppercase and is_short and is_not_empty and
            not s.startswith(('-', '*', '+', '|')) and
            is_not_date and is_not_location and is_not_signature):
            elements["headings"].append({"level": 1, "text": s})
            continue

        if s.startswith(('-', '*', '+')):
            current_list.append(s[1:].strip())
            continue
        elif re.match(r'^\d+\.', s):
            current_list.append(s.split('.', 1)[1].strip() if '.' in s else s)
            continue
        elif current_list and not s:
            elements["lists"].append(current_list)
            current_list = []
            continue

        if '|' in s and not is_uppercase:
            if not in_table:
                in_table = True
                current_table = []
            current_table.append([cell.strip() for cell in s.split('|')[1:-1]])
            continue
        elif in_table and not s:
            if current_table:
                elements["tables"].append(current_table)
            current_table = []
            in_table = False
            continue

        if (':' in s or ' - ' in s) and not is_uppercase:
            if ':' in s and not s.startswith('##'):
                parts = s.split(':', 1)
                if len(parts) == 2 and len(parts[0]) < 50:
                    elements["key_value_pairs"].append({"key": parts[0].strip(), "value": parts[1].strip()})
                    continue
            elif ' - ' in s and s.count(' - ') <= 3:
                parts = s.split(' - ', 1)
                if len(parts) == 2:
                    elements["key_value_pairs"].append({"key": parts[0].strip(), "value": parts[1].strip()})
                    continue

        elements["paragraphs"].append(s)

    if current_list:
        elements["lists"].append(current_list)
    if current_table:
        elements["tables"].append(current_table)

    return elements

def has_important_heading(parsed_elements):
    headings = parsed_elements["headings"]

    if not headings:
        return False, None, 0, []

    score = 0
    signals = []
    heading_type = None

    official_patterns = [
        "CONG HOA XA HOI CHU NGHIA VIET NAM",
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM"
    ]

    for heading in headings:
        heading_text = heading["text"]

        for pattern in official_patterns:
            found, ratio = fuzzy_contains(heading_text, pattern, threshold=0.7)
            if found:
                score += int(20 * ratio)
                signals.append(f"tiêu_ngữ({ratio:.2f})")
                heading_type = "tiêu_ngữ"
                return True, heading_type, score, signals

        if heading == headings[0]:
            text_upper = heading_text.upper()
            unit_keywords = [
                r'^BỘ\s+[A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ\s]+',
                r'^TRUNG\s*TÂM\s+[A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ\s]+',
                r'^CÔNG\s*TY\s+(TNHH|CP|CỔ\s*PHẦN)',
                r'^SỞ\s+[A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ\s]+',
                r'^PHÒNG\s+[A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ\s]+',
            ]

            for pattern in unit_keywords:
                if re.search(pattern, text_upper):
                    score += 15
                    signals.append("tên_đơn_vị")
                    heading_type = "tên_đơn_vị"
                    return True, heading_type, score, signals

    return False, None, score, signals

def detect_document_start(page_data):
    parsed_elements = page_data["content"]["parsed_elements"]
    has_heading, heading_type, score, signals = has_important_heading(parsed_elements)

    return {
        "is_document_start": has_heading,
        "score": score,
        "signals": signals,
        "heading_type": heading_type
    }

def segment_documents(ocr_pages):
    segments = []
    current_segment = None

    for page_data in ocr_pages:
        page_num = page_data["page_number"]
        raw_text = page_data["content"]["raw_markdown"]

        detection = detect_document_start(page_data)

        if detection["is_document_start"]:
            if current_segment:
                segments.append(current_segment)

            current_segment = {
                "segment_id": len(segments) + 1,
                "start_page": page_num,
                "end_page": page_num,
                "pages": [page_data],
                "full_text": raw_text,
                "page_count": 1,
                "detection_score": detection["score"],
                "detection_signals": detection["signals"],
                "heading_type": detection["heading_type"]
            }
        else:
            if current_segment:
                current_segment["end_page"] = page_num
                current_segment["pages"].append(page_data)
                current_segment["full_text"] += "\n\n" + raw_text
                current_segment["page_count"] += 1
            else:
                current_segment = {
                    "segment_id": len(segments) + 1,
                    "start_page": page_num,
                    "end_page": page_num,
                    "pages": [page_data],
                    "full_text": raw_text,
                    "page_count": 1,
                    "detection_score": 0,
                    "detection_signals": ["no_heading"],
                    "heading_type": "unknown"
                }

    if current_segment:
        segments.append(current_segment)

    return segments

def auto_detect_from_headings(headings, text):
    metadata = {
        "loai_van_ban": "Không xác định",
        "ten_ho_so": "",
        "so_ky_hieu": "",
        "don_vi_ban_hanh": "",
        "ngay_ban_hanh": ""
    }

    doc_types = {
        "Quyết định": [r'QUYẾT\s*ĐỊNH', r'QUYET\s*DINH'],
        "Tờ trình": [r'TỜ\s*TRÌNH', r'TO\s*TRINH'],
        "Thư mời quan tâm": [r'THƯ\s*MỜI\s*QUAN\s*TÂM'],
        "Biên bản": [r'BIÊN\s*BẢN', r'BIEN\s*BAN'],
        "Hợp đồng": [r'HỢP\s*ĐỒNG', r'HOP\s*DONG'],
        "Thông báo": [r'THÔNG\s*BÁO', r'THONG\s*BAO'],
        "Công văn": [r'CÔNG\s*VĂN', r'CONG\s*VAN'],
        "Báo cáo": [r'BÁO\s*CÁO', r'BAO\s*CAO']
    }

    found_type_text = None
    for heading in headings:
        heading_text = heading["text"]
        for doc_type, patterns in doc_types.items():
            for pattern in patterns:
                if re.search(pattern, heading_text, re.IGNORECASE):
                    metadata["loai_van_ban"] = doc_type
                    found_type_text = heading_text
                    break
            if metadata["loai_van_ban"] != "Không xác định":
                break
        if metadata["loai_van_ban"] != "Không xác định":
            break

    if found_type_text:
        lines = text.split('\n')
        type_line_idx = -1
        for idx, line in enumerate(lines):
            line_stripped = line.strip()
            if (found_type_text in line or
                re.search(r'(QUYẾT ĐỊNH|TỜ TRÌNH|BIÊN BẢN|HỢP ĐỒNG|THÔNG BÁO|CÔNG VĂN|BÁO CÁO)',
                         line_stripped, re.IGNORECASE)):
                if len(line_stripped) < 100:
                    type_line_idx = idx
                    break

        if type_line_idx >= 0:
            start_idx = type_line_idx + 1
            while start_idx < len(lines) and not lines[start_idx].strip():
                start_idx += 1

            if start_idx < len(lines):
                stop_keywords = [
                    "CỘNG HÒA", "ĐỘC LẬP", "HÀ NỘI", "LÃNH ĐẠO",
                    "CĂN CỨ", "THEO ĐỀ NGHỊ", "XÉT ĐỀ NGHỊ",
                    "QUYẾT ĐỊNH:", "TỜ TRÌNH:", "Số:", "Điều 1"
                ]

                ten_ho_so_lines = []
                current_idx = start_idx

                while current_idx < len(lines) and len(ten_ho_so_lines) < 10:
                    line = lines[current_idx].strip()

                    if any(kw in line.upper() for kw in stop_keywords):
                        break

                    if re.search(r'ngày\s+\d{1,2}\s+tháng\s+\d{1,2}\s+năm\s+\d{4}', line, re.IGNORECASE):
                        break

                    if not line and ten_ho_so_lines:
                        if current_idx + 1 < len(lines):
                            next_line = lines[current_idx + 1].strip()
                            if next_line and (next_line[0].islower() or not next_line[0].isupper()):
                                current_idx += 1
                                continue
                        break

                    if line:
                        ten_ho_so_lines.append(line)

                    current_idx += 1

                if ten_ho_so_lines:
                    ten_ho_so = " ".join(ten_ho_so_lines)
                    ten_ho_so = re.sub(r'\s+', ' ', ten_ho_so).strip()
                    ten_ho_so = re.sub(r'^\d+[\.\)]\s*', '', ten_ho_so)

                    if len(ten_ho_so) >= 15 and len(ten_ho_so) <= 500:
                        metadata["ten_ho_so"] = ten_ho_so

    so_patterns = [
        r'Số\s*[:.]?\s*([0-9/\-A-ZĐ]+)',
        r'([0-9]+/[A-ZĐ]{2,4}[-\s][A-ZĐ0-9]{2,10})'
    ]
    for pattern in so_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            so = match.group(1).strip()
            if len(so) >= 5 and '/' in so:
                metadata["so_ky_hieu"] = so
                break

    for h in headings[:4]:
        h_text = h["text"]
        if any(keyword in h_text.upper() for keyword in ["BỘ ", "TRUNG TÂM", "CÔNG TY", "SỞ ", "PHÒNG ", "VIỆN "]):
            if "CỘNG HÒA" not in h_text.upper() and "ĐỘC LẬP" not in h_text.upper():
                metadata["don_vi_ban_hanh"] = h_text
                break

    date_match = re.search(r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})', text, re.IGNORECASE)
    if date_match:
        metadata["ngay_ban_hanh"] = f"ngày {date_match.group(1)} tháng {date_match.group(2)} năm {date_match.group(3)}"

    return metadata

# ==================== EXTRACTION (IMPROVED v3) ====================

def extract_value_by_numbered_pattern(text, pattern_prefix, min_len=10, max_len=500):
    patterns = [
        rf'\d+\.\s*{pattern_prefix}\s*[:：]\s*([^\n]+?)(?=\n\d+\.|$)',
        rf'{pattern_prefix}\s*[:：]\s*([^\n]+?)(?=\n\d+\.|$)',
        rf'{pattern_prefix}\s*[:：]\s*([^\n]+?)(?=\n[A-Z]|$)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            value = re.sub(r'^\d+[\.\)]\s*', '', value)
            value = value.replace('\n', ' ').strip()
            value = re.split(r'(?:Địa điểm|Nhóm dự án|Nội dung|Địa chỉ|Tổng mức)', value)[0].strip()

            if min_len <= len(value) <= max_len:
                return value

    return ""

def extract_money_amount(text):
    patterns = [
        r'Tổng\s*mức\s*đầu\s*tư\s*[:：]?\s*([\d\.,\s]+)\s*(?:VN[ĐD]|đồng|tỷ|triệu)',
        r'TỔNG\s*CỘNG\s*\(?làm\s*tròn\)?(?:\s*[:：])?\s*([\d\.,\s]+)\s*(?:VN[ĐD]|đồng)',
        r'([\d]{1,3}(?:\.|,)?[\d]{3}(?:\.|,)?[\d]{3}(?:\.|,)?[\d]{0,3})\s*(?:VN[ĐD]|đồng|triệu|tỷ)',
        r'Kinh phí[:：]?\s*([\d\.,\s]+)\s*(?:VN[ĐD]|đồng)',
    ]

    all_amounts = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            num_str = match.strip()
            num_str = re.sub(r'[\s,]', '', num_str)
            num_str = re.sub(r'\.', '', num_str)

            if len(num_str) >= 6 and num_str.isdigit():
                amount_int = int(num_str)
                formatted = match.strip().replace(' ', '')
                all_amounts.append((amount_int, formatted))

    if all_amounts:
        max_amount = max(all_amounts, key=lambda x: x[0])
        result = max_amount[1]

        if 'VND' not in result.upper() and 'VNĐ' not in result.upper():
            result += " VND"

        return result

    return ""

def extract_date(text, date_type="ngay_ban_hanh"):
    if date_type == "ngay_ban_hanh":
        date_patterns = [
            r'(?:ngày lập|ngày ban hành|ngày)\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})',
            r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})',
        ]
    else:
        date_patterns = [r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})']

    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            day, month, year = match.groups()
            return f"ngày {day} tháng {month} năm {year}"

    return ""

def detect_project_group(text):
    patterns = [r'(?:Dự án\s+)?nhóm\s+([ABC])', r'nhóm\s*[:：]\s*([ABC])']

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f"Dự án nhóm {match.group(1).upper()}"

    return ""

def detect_work_type(text):
    work_types = {
        "Xây dựng": r'(xây dựng|xây\s+dựng)',
        "Mua sắm": r'(mua sắm|máy móc|thiết bị)',
        "Cải tạo": r'(cải tạo|sửa chữa|nâng cấp)',
        "Nghiên cứu": r'(nghiên cứu|khảo sát)',
        "Phần mềm": r'(phần mềm|software|hệ thống|cntt)',
    }

    text_lower = text.lower()
    for work_type, pattern in work_types.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            return work_type

    return ""

def detect_work_grade(text):
    patterns = [
        (r'cấp\s+(?:I|1)\b', "Cấp I"),
        (r'cấp\s+(?:II|2)\b', "Cấp II"),
        (r'cấp\s+(?:III|3)\b', "Cấp III"),
        (r'cấp\s+(?:IV|4)\b', "Cấp IV"),
        (r'cấp\s+(?:V|5)\b', "Cấp V"),
    ]

    for pattern, label in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return label

    return ""

def detect_time_period(text):
    patterns = [
        r'Quý\s*(?:I{1,3}|IV)\s*/\s*(\d{4})',
        r'Năm\s*(\d{4})',
        r'(\d{1,2})/(\d{1,2})/(\d{4})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)

    return ""

def extract_fund_source(text):
    fund_sources = {
        "Ngân sách Nhà nước": r'ngân\s*sách\s*(?:nhà nước|trung ương|địa phương)',
        "Vốn tư nhân": r'vốn\s*tư\s*(?:nhân|thực hiện)',
        "Vốn ODA": r'ODA|vốn\s+nước\s+ngoài',
        "Vốn kết hợp": r'(?:kết hợp|hỗn hợp)\s+(?:công tư|nhà nước)',
        "Vốn doanh nghiệp": r'(?:doanh nghiệp|công ty)',
    }

    for source, pattern in fund_sources.items():
        if re.search(pattern, text, re.IGNORECASE):
            return source

    return ""

def extract_document_info_improved(text, classification):
    text_clean = clean_text(text)
    result = {}

    result["loai_van_ban"] = classification.get("loai_van_ban", "Không xác định")
    result["loai_cong_van"] = classification.get("loai_van_ban", "")
    result["ten_day_du"] = classification.get("ten_ho_so", "")

    ma_patterns = [
        r'Mã\s*(?:dự\s*án|dự\s*án\s*:)\s*([A-Z0-9\-/]{5,30})',
        r'Mã\s*[:：]\s*([A-Z0-9\-/]{5,30})',
    ]
    for pattern in ma_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            result["ma_du_an"] = match.group(1).strip()
            break

    ten_du_an = extract_value_by_numbered_pattern(text, "Tên dự án", min_len=20, max_len=200)
    if ten_du_an:
        result["ten_du_an"] = ten_du_an[:250]
    elif result.get("ten_day_du") and len(result["ten_day_du"]) < 300:
        result["ten_du_an"] = result["ten_day_du"][:250]

    chu_dau_tu = extract_value_by_numbered_pattern(text, "Chủ đầu tư", min_len=5, max_len=150)
    if chu_dau_tu:
        result["chu_dau_tu"] = chu_dau_tu
    else:
        don_vi = classification.get("don_vi_ban_hanh", "")
        if don_vi and len(don_vi) > 3:
            result["chu_dau_tu"] = don_vi[:150]

    muc_tieu = extract_value_by_numbered_pattern(text, "Mục tiêu", min_len=30, max_len=500)
    if muc_tieu:
        result["muc_tieu_du_an"] = muc_tieu[:400]

    quy_mo = extract_money_amount(text)
    if quy_mo:
        result["quy_mo_dau_tu"] = quy_mo

    nguon_von = extract_fund_source(text)
    if nguon_von:
        result["loai_nguon_von"] = nguon_von
    else:
        nguon_text = extract_value_by_numbered_pattern(text, "Nguồn vốn", min_len=10, max_len=200)
        if nguon_text:
            result["loai_nguon_von"] = nguon_text[:200]

    status_keywords = {
        "Đang thực hiện": r'đang\s+(?:thực\s+hiện|tiến\s+hành)',
        "Hoàn thành": r'(?:hoàn\s+thành|kết\s+thúc)',
        "Chưa bắt đầu": r'chưa\s+(?:bắt\s+đầu|khởi\s+công)',
        "Tạm dừng": r'tạm\s+dừng',
    }
    for status, pattern in status_keywords.items():
        if re.search(pattern, text, re.IGNORECASE):
            result["trang_thai_du_an"] = status
            break

    linh_vuc_keywords = {
        "Công nghệ thông tin": [r'phần mềm', r'cntt', r'công nghệ thông tin', r'it'],
        "Xây dựng": [r'xây dựng', r'công trình', r'cấu trúc'],
        "Y tế": [r'y tế', r'bệnh viện', r'khám chữa'],
        "Giáo dục": [r'giáo dục', r'đào tạo', r'học'],
        "Giao thông": [r'giao thông', r'đường', r'cầu'],
    }

    text_lower = text.lower()
    for linh_vuc, keywords in linh_vuc_keywords.items():
        for keyword in keywords:
            if re.search(keyword, text_lower, re.IGNORECASE):
                result["linh_vuc"] = linh_vuc
                break
        if "linh_vuc" in result:
            break

    nhom = detect_project_group(text)
    if nhom:
        result["nhom_du_an"] = nhom

    loai_cong_trinh = detect_work_type(text)
    if loai_cong_trinh:
        result["loai_cong_trinh"] = loai_cong_trinh

    cap_cong_trinh = detect_work_grade(text)
    if cap_cong_trinh:
        result["cap_cong_trinh"] = cap_cong_trinh

    thoi_gian_khoi_cong = extract_value_by_numbered_pattern(
        text, "(?:Thời gian|Dự kiến).*khởi công", min_len=5, max_len=100
    )
    if thoi_gian_khoi_cong:
        result["thoi_gian_du_kien_khoi_cong"] = thoi_gian_khoi_cong[:100]

    thoi_gian_hoan_thanh = extract_value_by_numbered_pattern(
        text, "(?:Thời gian|Dự kiến).*hoàn thành", min_len=5, max_len=100
    )
    if thoi_gian_hoan_thanh:
        result["thoi_gian_du_kien_hoan_thanh"] = thoi_gian_hoan_thanh[:100]

    thoi_gian_thuc_hien = extract_value_by_numbered_pattern(
        text, "(?:Thời gian|Thời hạn)(?:\s+thực\s+hiện)?", min_len=5, max_len=100
    )
    if not thoi_gian_thuc_hien:
        thoi_gian_thuc_hien = detect_time_period(text)

    if thoi_gian_thuc_hien:
        result["thoi_gian_thuc_hien_du_an"] = thoi_gian_thuc_hien[:100]

    thoi_gian_ket_thuc = extract_value_by_numbered_pattern(
        text, "(?:Thời gian|Ngày).*kết thúc", min_len=5, max_len=100
    )
    if thoi_gian_ket_thuc:
        result["thoi_gian_ket_thuc_du_an"] = thoi_gian_ket_thuc[:100]

    so_qd = classification.get("so_ky_hieu", "")
    if so_qd:
        result["so_quyet_dinh"] = so_qd

    ngay_qd = extract_date(text, "ngay_ban_hanh")
    if ngay_qd:
        result["ngay_quyet_dinh"] = ngay_qd
    elif classification.get("ngay_ban_hanh"):
        result["ngay_quyet_dinh"] = classification.get("ngay_ban_hanh")

    result["don_vi_tien_te"] = "VND"
    result["trang_thai_thanh_tra"] = ""
    result["trang_thai_kiem_toan"] = ""
    result["don_vi_xu_ly_quyet_toan"] = ""
    result["hinh_thuc_quan_ly"] = ""

    return result

# ==================== OCR PROCESSOR ====================

class DocumentOCRProcessor:
    def __init__(self):
        self.ocr_manager = None
        self.embedding_model = None
        self.llm_model = None
        self.tokenizer = None
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return

        print("🔄 Loading Chandra OCR...")
        try:
            self.ocr_manager = InferenceManager(method="hf")
            print("✅ Chandra OCR ready")
        except Exception as e:
            print(f"❌ Chandra OCR error: {e}")
            raise

        print("🔄 Loading Embedding Model...")
        try:
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            print(f"✅ {EMBEDDING_MODEL} ready")
        except Exception as e:
            print(f"⚠️ Embedding error: {e}")

        self._initialized = True

    def process_single_page(self, img, page_num):
        try:
            batch_item = BatchInputItem(image=img, prompt_type="ocr_layout")
            result = self.ocr_manager.generate([batch_item])

            if result and len(result) > 0:
                ocr_output = result[0]
                if hasattr(ocr_output, 'markdown'):
                    markdown = ocr_output.markdown.strip()
                elif hasattr(ocr_output, 'raw'):
                    markdown = str(ocr_output.raw).strip()
                else:
                    markdown = str(ocr_output).strip()

                return {
                    "page": page_num,
                    "markdown": markdown,
                    "raw": getattr(ocr_output, 'raw', None),
                    "image_size": img.size,
                    "success": True,
                    "error": None
                }
            else:
                return {
                    "page": page_num,
                    "markdown": "",
                    "raw": None,
                    "image_size": img.size,
                    "success": False,
                    "error": "Không có kết quả"
                }
        except Exception as e:
            return {
                "page": page_num,
                "markdown": "",
                "raw": None,
                "image_size": img.size,
                "success": False,
                "error": str(e)
            }

    def process_pdf(self, pdf_path, dpi=DPI):
        try:
            images = convert_from_path(pdf_path, dpi=dpi, fmt='png', thread_count=4)
            if MAX_PAGES:
                images = images[:MAX_PAGES]

            print(f"📄 {len(images)} pages to process")
        except Exception as e:
            print(f"❌ PDF conversion error: {e}")
            return {"error": str(e), "pages": []}

        all_results = []

        def ocr_batch(batch_data):
            results = []
            for page_num, img in batch_data:
                result = self.process_single_page(img, page_num)
                results.append(result)
            return results

        batches = []
        for i in range(0, len(images), BATCH_SIZE):
            batch = [(i+j+1, images[i+j]) for j in range(min(BATCH_SIZE, len(images)-i))]
            batches.append(batch)

        start_ocr = time.time()

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(ocr_batch, batch): batch for batch in batches}
            for future in as_completed(futures):
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    print(f"❌ Batch error: {e}")

        all_results.sort(key=lambda x: x["page"])
        elapsed_ocr = time.time() - start_ocr
        success = sum(1 for r in all_results if r["success"])

        print(f"✅ OCR: {success}/{len(images)} pages in {elapsed_ocr:.1f}s")
        
        return {
            "total_pages": len(images),
            "successful_pages": success,
            "pages": all_results,
            "processing_time": elapsed_ocr
        }

    def classify_document(self, segment_text, headings):
        return auto_detect_from_headings(headings, segment_text)

    def extract_document_info(self, segment_text, classification):
        return extract_document_info_improved(segment_text, classification)

# ==================== FASTAPI SERVER ====================

app = FastAPI(title="Document OCR API - Final", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

processor = DocumentOCRProcessor()
processor.initialize()

@app.middleware("http")
async def add_ngrok_bypass_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        return JSONResponse(
            content={},
            status_code=200,
            headers={
                "ngrok-skip-browser-warning": "69420",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "69420"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, detail="Chỉ chấp nhận file PDF")

        pdf_bytes = await file.read()
        size = len(pdf_bytes)

        if size > MAX_FILE_SIZE:
            raise HTTPException(400, detail=f"File quá lớn (max {MAX_FILE_SIZE/1024/1024}MB)")

        if not pdf_bytes.startswith(b"%PDF"):
            raise HTTPException(400, detail="File không phải PDF hợp lệ")

        doc_id = hashlib.md5((file.filename + str(size)).encode()).hexdigest()[:12]
        saved_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"

        with open(saved_path, "wb") as f:
            f.write(pdf_bytes)

        documents_storage[doc_id] = {
            "document_id": doc_id,
            "file_name": file.filename,
            "saved_path": str(saved_path),
            "size": size,
            "uploaded_at": datetime.now().isoformat()
        }

        print(f"✅ Document uploaded: {doc_id}")

        return {
            "status": "success",
            "document_id": doc_id,
            "file_name": file.filename,
            "size_mb": round(size / (1024 * 1024), 2)
        }
    except Exception as e:
        print(f"❌ Upload error: {e}")
        raise HTTPException(500, detail=str(e))

async def run_full_extraction(document_id, dpi):
    if document_id not in documents_storage:
        print(f"❌ Document {document_id} not found")
        return

    with ocr_global_lock:
        doc_path = documents_storage[document_id]["saved_path"]
        print(f"\n🕒 Full extraction started for {document_id}")

        print("\n📄 STEP 1: OCR Processing...")
        ocr_result = processor.process_pdf(doc_path, dpi)

        if ocr_result.get("error"):
            print(f"❌ OCR error: {ocr_result['error']}")
            ocr_results_cache[document_id] = {"error": ocr_result['error']}
            return

        ocr_pages = ocr_result["pages"]

        print("\n📊 STEP 2: Parsing Markdown...")
        parsed_pages = []
        for page_result in ocr_pages:
            if not page_result["success"]:
                continue

            elements = parse_markdown(page_result["markdown"])

            parsed_page = {
                "page_number": page_result["page"],
                "image_size": {"width": page_result["image_size"][0], "height": page_result["image_size"][1]},
                "content": {
                    "raw_markdown": page_result["markdown"],
                    "parsed_elements": elements
                },
                "stats": {
                    "text_length": len(page_result["markdown"]),
                    "num_headings": len(elements["headings"]),
                    "num_paragraphs": len(elements["paragraphs"]),
                    "num_lists": len(elements["lists"]),
                    "num_tables": len(elements["tables"]),
                    "num_key_value_pairs": len(elements["key_value_pairs"])
                }
            }
            parsed_pages.append(parsed_page)

        print(f"✅ Parsed {len(parsed_pages)} pages")

        print("\n📑 STEP 3: Document Segmentation...")
        segments = segment_documents(parsed_pages)
        print(f"✅ Found {len(segments)} documents")

        print("\n🏷️  STEP 4: Classification & Extraction...")
        detailed_extractions = []

        for segment in segments:
            first_page = segment["pages"][0]
            headings = first_page["content"]["parsed_elements"]["headings"]

            classification = processor.classify_document(segment["full_text"], headings)
            extracted = processor.extract_document_info(segment["full_text"], classification)

            full_data = {
                "segment_id": segment["segment_id"],
                "start_page": segment["start_page"],
                "end_page": segment["end_page"],
                "page_count": segment["page_count"],
                "loai_van_ban": classification["loai_van_ban"],
                "ten_day_du": classification["ten_ho_so"],
                "ma_du_an": extracted.get("ma_du_an", ""),
                "ten_du_an": extracted.get("ten_du_an", ""),
                "chu_dau_tu": extracted.get("chu_dau_tu", ""),
                "muc_tieu_du_an": extracted.get("muc_tieu_du_an", ""),
                "quy_mo_dau_tu": extracted.get("quy_mo_dau_tu", ""),
                "loai_nguon_von": extracted.get("loai_nguon_von", ""),
                "trang_thai_du_an": extracted.get("trang_thai_du_an", ""),
                "trang_thai_thanh_tra": extracted.get("trang_thai_thanh_tra", ""),
                "trang_thai_kiem_toan": extracted.get("trang_thai_kiem_toan", ""),
                "nhom_du_an": extracted.get("nhom_du_an", ""),
                "linh_vuc": extracted.get("linh_vuc", ""),
                "don_vi_xu_ly_quyet_toan": extracted.get("don_vi_xu_ly_quyet_toan", ""),
                "loai_cong_trinh": extracted.get("loai_cong_trinh", ""),
                "cap_cong_trinh": extracted.get("cap_cong_trinh", ""),
                "hinh_thuc_quan_ly": extracted.get("hinh_thuc_quan_ly", ""),
                "thoi_gian_du_kien_khoi_cong": extracted.get("thoi_gian_du_kien_khoi_cong", ""),
                "thoi_gian_du_kien_hoan_thanh": extracted.get("thoi_gian_du_kien_hoan_thanh", ""),
                "thoi_gian_thuc_hien_du_an": extracted.get("thoi_gian_thuc_hien_du_an", ""),
                "thoi_gian_ket_thuc_du_an": extracted.get("thoi_gian_ket_thuc_du_an", ""),
                "don_vi_tien_te": "VND",
                "so_quyet_dinh": extracted.get("so_quyet_dinh", ""),
                "ngay_quyet_dinh": extracted.get("ngay_quyet_dinh", ""),
                "loai_cong_van": extracted.get("loai_cong_van", "")
            }

            detailed_extractions.append(full_data)
            print(f"  ✓ Document {segment['segment_id']}: {classification['loai_van_ban']}")

        print("\n💾 STEP 5: Saving Results...")

        output_data = {
            "metadata": {
                "document_id": document_id,
                "file_name": documents_storage[document_id]["file_name"],
                "total_pages": len(ocr_pages),
                "successful_ocr_pages": sum(1 for p in ocr_pages if p["success"]),
                "total_documents": len(segments),
                "processed_at": datetime.now().isoformat(),
            },
            "ocr_results": ocr_result,
            "parsed_pages": parsed_pages,
            "segments": segments,
            "extractions": detailed_extractions
        }

        ocr_results_cache[document_id] = output_data

        json_path = OUTPUT_DIR / f"{document_id}_full_extraction.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        csv_path = OUTPUT_DIR / f"{document_id}_extractions.csv"
        if detailed_extractions:
            fieldnames = list(detailed_extractions[0].keys())
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in detailed_extractions:
                    writer.writerow(row)

        print(f"✅ Results saved to {json_path}")
        print(f"✅ Extractions saved to {csv_path}")
        
        # Notify WebSocket clients - Đơn giản hơn vì hàm đã là async
        try:
            await manager.send_completion(document_id, {
                "status": "completed",
                "document_id": document_id,
                "message": "OCR extraction hoàn thành",
                "total_documents": len(detailed_extractions)
            })
        except Exception as e:
            print(f"⚠️ WebSocket notification error: {e}")

@app.post("/api/v1/documents/{document_id}/extract_full_async")
async def extract_full_async(
    document_id: str,
    background_tasks: BackgroundTasks,
    dpi: int = Query(300)
):
    if document_id not in documents_storage:
        raise HTTPException(404, detail="Tài liệu không tồn tại")

    if document_id in ocr_results_cache:
        return {
            "status": "completed",
            "document_id": document_id,
            "message": "Extraction đã hoàn thành"
        }

    background_tasks.add_task(run_full_extraction, document_id, dpi)

    return {
        "status": "processing",
        "document_id": document_id,
        "message": "Full extraction đang xử lý, vui lòng gọi API lấy kết quả sau"
    }

@app.get("/api/v1/documents/{document_id}/extraction_result")
async def get_extraction_result(document_id: str):
    if document_id not in ocr_results_cache:
        return {
            "status": "pending",
            "document_id": document_id,
            "message": "Kết quả chưa có, vui lòng đợi"
        }

    return {
        "status": "completed",
        "document_id": document_id,
        "data": ocr_results_cache[document_id]
    }

@app.get("/api/v1/documents/{document_id}/extractions")
async def get_extractions(document_id: str):
    if document_id not in ocr_results_cache:
        return {
            "status": "pending",
            "message": "Dữ liệu chưa có"
        }

    data = ocr_results_cache[document_id]
    if "extractions" in data:
        return {
            "status": "success",
            "document_id": document_id,
            "total_documents": len(data["extractions"]),
            "extractions": data["extractions"]
        }

    return {
        "status": "error",
        "message": "Không tìm thấy dữ liệu trích xuất"
    }

@app.get("/api/v1/documents")
async def list_documents():
    return {
        "total": len(documents_storage),
        "documents": list(documents_storage.values())
    }

@app.get("/")
async def root():
    return {
        "message": "Document OCR API - Final v3.0",
        "status": "ready"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws/{document_id}")
async def websocket_endpoint(websocket: WebSocket, document_id: str):
    await manager.connect(websocket, document_id)
    try:
        # Check if already completed
        if document_id in ocr_results_cache:
            await websocket.send_json({
                "status": "completed",
                "document_id": document_id,
                "message": "OCR đã hoàn thành trước đó"
            })
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"status": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, document_id)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        manager.disconnect(websocket, document_id)

# Chạy server uvicorn trong background thread (Colab compatibility)
def run_server():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    from pyngrok import ngrok

    NGROK_TOKEN = "35grPC2jHWgMqp8B63zzoPeMcnO_5ycCqzJxZ5S5rQsLzerN9"
    ngrok.set_auth_token(NGROK_TOKEN)
    public_url = ngrok.connect(8000)
    print(f"📡 [translate:Public URL]: {public_url}")

    import threading
    import time

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n✋ [translate:Server đã dừng]")