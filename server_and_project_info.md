# Hệ thống Server & Projects

## Tổng quan

| Server| Vai trò chính |
|--------|---------------|
| ecs-nbg | AI/ML Services (OCR, Face Recognition, Speech-to-Text, RAG) |
| k8s-master-1 | Backend API + Monitoring Stack |
| k8s-master-2 | Harbor Registry + Document Converters + Jira |

---

## Server: ecs-nbg (AI/ML Services)

### AI Services

| Container | Image | Port | Chức năng |
|-----------|-------|------|-----------|
| vllmnanoocr_v2 | manhdoan291/vllm_nanoocr_v1:v1 | 7869, 8059, 9059 | OCR + LLM - Trích xuất text từ ảnh/PDF |
| vintern-parser-api | streaming_document_parser_v2 | 7861, 8081 | Document Parser (model Vintern) |
| deepface | serengil/deepface:latest | 5005 | Face Recognition |
| whisper_api_server | whisper_api_server | 9033 | Speech-to-Text |
| backend-app | backend-rag-local_backend | 3000 | Backend API (RAG) |

### Data Layer

| Container | Image | Port | Chức năng |
|-----------|-------|------|-----------|
| milvus-standalone | milvusdb/milvus:v2.5.13 | 19530 | Vector Database |
| mongodb | mongo:6.0 | 27017 | Document Database |
| milvus-etcd | quay.io/coreos/etcd:v3.5.18 | - | Key-value store cho Milvus |
| milvus-minio | minio/minio | 9000-9001 | Object Storage cho Milvus |

---

## Server: k8s-master-1 (Backend + Monitoring)

### Backend Services - DEV Environment

| Container | Port | Chức năng |
|-----------|------|-----------|
| dev-be-api-1 | 5006 | API chính (dev) |
| dev-be-socket-1 | 5002 | WebSocket server (dev) |
| dev-be-worker-1 | - | Background worker (dev) |
| dev-be-cron-1 | - | Scheduled jobs (dev) |

### Backend Services - PROD Environment

| Container | Port | Chức năng |
|-----------|------|-----------|
| be-api-1 | 5005 | API chính (prod) |
| be-socket-1 | 5001 | WebSocket server (prod) |
| be-worker-1 | - | Background worker (prod) |
| be-cron-1 | - | Scheduled jobs (prod) |
| be-cms-1 | - | CMS backend (prod) |

### AI Services

| Container | Port | Chức năng |
|-----------|------|-----------|
| dev_ai_rag_local | 6979 | RAG AI server (dev) |
| dev_ai_rag_local_mcp | 8022 | MCP Tool server (dev) |
| agentic_server_duoc | 6970 | Agentic AI server |
| agentic_mcp_tool_server_duoc | 8003 | MCP Tool server |

### Infrastructure

| Container | Port | Chức năng |
|-----------|------|-----------|
| dev_mongodb | 27018 | MongoDB (dev) |
| dev_redis | 6379 | Redis cache |
| dev_rabbitmq | 5672, 15672 | Message queue |
| elasticsearch | 9200, 9300 | Search engine |
| minio | 9000-9001 | Object storage |
| cloudflared | - | Cloudflare tunnel |

### Monitoring Stack

| Container | Port | Chức năng |
|-----------|------|-----------|
| grafana | 3000 | Dashboard UI |
| prometheus | 9090 | Metrics collection |
| loki | 3100 | Log aggregation |
| promtail | - | Log shipper |
| node-exporter | - | System metrics |
| cadvisor | 8081 | Container metrics |
| grafana-lark | 5000 | Alert to Lark |
| uptime-kuma | 3001 | Uptime monitoring |

---

## Server: k8s-master-2 (Harbor + Tools)

### Harbor Registry (Private Docker Registry)

| Container | Port | Chức năng |
|-----------|------|-----------|
| nginx | 8081 | Harbor proxy/gateway |
| harbor-core | - | Harbor core service |
| harbor-portal | - | Harbor web UI |
| harbor-jobservice | - | Background jobs |
| harbor-db | - | PostgreSQL cho Harbor |
| registry | - | Docker registry storage |

**Harbor UI:** `http://124.158.4.89:8081`

### Document Converter Services

| Container | Port | Chức năng |
|-----------|------|-----------|
| fastapi-app | 8091 | AI to DOCX converter |
| docx-converter-nginx | 3000 | Nginx load balancer |
| nbg-convert-api-app-1 | 3000 | Convert API instance 1 |
| nbg-convert-api-app-2 | 3000 | Convert API instance 2 |
| docx-converter-gotenberg | 3031 | Gotenberg (PDF/Office converter) |
| docx-converter-mongodb | 27031 | MongoDB cho converter |

### Project Management

| Container | Port | Chức năng |
|-----------|------|-----------|
| jira-srv | 8989 | Jira (issue tracking) |
| mysql-jira | 3306 | MySQL cho Jira |

### Infrastructure

| Container | Port | Chức năng |
|-----------|------|-----------|
| mongodb-nbg-hightech | 27026 | MongoDB |
| minio-dev | 9000-9001 | Object storage (dev) |
| redis | 6379 | Redis cache |
| rabbitmq | 5672, 15672 | Message queue |

### Monitoring Agents

| Container | Chức năng |
|-----------|-----------|
| cadvisor | Container metrics → Prometheus |
| promtail | Log shipper → Loki |
| node-exporter | System metrics → Prometheus |

---

## Kiến trúc tổng quan

```
                         Internet
                            │
                    ┌───────▼───────┐
                    │  Cloudflare   │
                    │    Tunnel     │
                    └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   ecs-nbg     │   │ k8s-master-1  │   │ k8s-master-2  │
│               │   │               │   │               │
│  AI/ML Stack  │   │ Backend APIs  │   │ Harbor        │
│  - OCR        │   │ - DEV (5006)  │   │ Registry      │
│  - DeepFace   │   │ - PROD (5005) │   │ (8081)        │
│  - Whisper    │   │               │   │               │
│  - RAG        │   │ Monitoring    │   │ Doc Converter │
│               │   │ - Grafana     │   │ - Gotenberg   │
│  Milvus       │   │ - Prometheus  │   │               │
│  MongoDB      │   │ - Loki        │   │ Jira (8989)   │
└───────────────┘   └───────────────┘   └───────────────┘
```

---

## Ports Summary

| Port | Service | Server |
|------|---------|--------|
| 3000 | Grafana / Backend RAG | k8s-master-1 / ecs-nbg |
| 3001 | Uptime Kuma | k8s-master-1 |
| 3100 | Loki | k8s-master-1 |
| 5001 | WebSocket (prod) | k8s-master-1 |
| 5002 | WebSocket (dev) | k8s-master-1 |
| 5005 | API (prod) / DeepFace | k8s-master-1 / ecs-nbg |
| 5006 | API (dev) | k8s-master-1 |
| 5672 | RabbitMQ | k8s-master-1, k8s-master-2 |
| 6379 | Redis | k8s-master-1, k8s-master-2 |
| 6979 | RAG AI (dev) | k8s-master-1 |
| 8081 | Harbor | k8s-master-2 |
| 8989 | Jira | k8s-master-2 |
| 9033 | Whisper | ecs-nbg |
| 9090 | Prometheus | k8s-master-1 |
| 9200 | Elasticsearch | k8s-master-1 |
| 19530 | Milvus | ecs-nbg |
| 27017-27031 | MongoDB | various |