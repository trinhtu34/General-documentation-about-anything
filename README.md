# Cấu trúc và vị trí file của tính năng chat với AI

## 1. Core Layer (Domain Entities)

### Entity Classes
```
src/Zero.Core/Abp/Chat/
├── AIChatConversation.cs          # Entity lưu thông tin conversation
└── AIChatMessage.cs                # Entity lưu tin nhắn trong conversation
```

### Configuration Classes
```
src/Zero.Core/Customize/AI/
└── AIProviderSettings.cs           # Cấu hình AI provider (OpenAI, Gemini, Ollama)
```

## 2. Application Layer

### DTOs
```
src/Zero.Application.Shared/Customize/AI/Dto/
├── AIChatDto.cs                    # SendMessageInput, AIChatResponse, AIProviderDto
├── AIStreamDto.cs                  # DTO cho streaming response
└── ConversationMessage.cs          # DTO cho tin nhắn trong context
```

### Application Service Interface
```
src/Zero.Application.Shared/Customize/AI/
└── IAIAppService.cs                # Interface định nghĩa các method của AI service
```

### Application Service Implementation
```
src/Zero.Application/Customize/AI/
├── AIAppService.cs                 # Service xử lý logic chat với AI
├── UniversalAIProvider.cs          # Provider gọi API các AI khác nhau
└── ConversationContextService.cs   # Service quản lý ngữ cảnh conversation (Redis)
```

## 3. Web Layer (MVC)

### Controller
```
src/Zero.Web.Core/Controllers/
└── DebugController.cs              # Controller debug Redis và conversation context
```

### View
```
src/Zero.Web.Mvc/Areas/App/Views/
└── [YourAIChatView]/               # View cho giao diện chat AI
    ├── Index.cshtml
    └── _ChatModal.cshtml
```

### JavaScript
```
src/Zero.Web.Mvc/wwwroot/view-resources/Areas/App/
└── [YourAIChatView]/               # JavaScript xử lý chat UI
    ├── Index.js
    └── _ChatModal.js
```

### Debug/Test Files
```
src/Zero.Web.Mvc/wwwroot/
└── debug-redis.html                # HTML test Redis và conversation context
```

## 4. Database Layer

### DbContext
```
src/Zero.EntityFrameworkCore/EntityFrameworkCore/
└── ZeroDbContext.cs                # Khai báo DbSet<AIChatConversation>, DbSet<AIChatMessage>
```

## 5. Configuration

### App Settings
```
src/Zero.Web.Mvc/
└── appsettings.json                # Cấu hình AI providers và Redis
    ├── AIProviders[]               # Danh sách AI providers (ChatGPT, Gemini, Ollama)
    └── Abp.RedisCache              # Cấu hình Redis cho conversation context
```

### Startup Configuration
```
src/Zero.Web.Core/
└── ZeroWebCoreModule.cs            # Enable Redis cache trong PreInitialize()
```

### Docker Configuration
```
/
└── docker-compose.yaml             # Cấu hình Redis container và Redis Commander
```

---

## Tóm tắt luồng hoạt động:

1. **User gửi tin nhắn** → Frontend (JS) → AIAppService
2. **AIAppService** → ConversationContextService lấy lịch sử từ Redis
3. **AIAppService** → UniversalAIProvider gọi AI API với context
4. **AI response** → Lưu vào Redis → Trả về Frontend
5. **Database** → Lưu conversation và messages vào SQL Server (optional)

# Clone Repository này về

```bash
git clone https://github.com/trinhtu34/General-documentation-about-anything.git
```
# Tải Docker Desktop

1. Tải và cài đặt Docker Desktop từ: https://www.docker.com/products/docker-desktop/
2. Khởi động Docker Desktop

**Lưu ý: Rất có thể khi tải docker desktop và khởi động sẽ gặp lỗi. Cụ thể lỗi này liên quan tới WSL ( Windows Subsystem Linux ) trên máy tính. Nếu thấy bất kỳ Error nào, hãy liên hệ Tú ngay!**

# Setup Redis

Để tải Redis trên Docker, làm như sau:

1. **Chạy docker compose:**
```bash
cd General-documentation-about-anything
docker-compose up -d

```

# Setup Project

**Yêu cầu: Vị trí của Terminal nằm tại thư mục root của project, là thư mục chứa file .sln ý. Example: PS D:\Company_Folder\qldac12>**

```bash
git clone https://git.368up.com/scm/zero103/qldac12.git
cd qldac12
git checkout -b Feature/QLDAC12-16
git pull origin Feature/QLDAC12-16
# Tại đây sẽ có thể hiện ra 1 bảng, đại loại nó thông báo conflic, để thoát và lưu chỉ cần gõ như sau
:qa
npm install
cd src/Zero.EntityFrameworkCore
dotnet ef migrations add Added_All
dotnet ef database update
cd ..
cd Zero.Web.Mvc
yarn install
# This command can be error, because gulp can be exist in this project
npm install gulp-cli -g
gulp buildDev
dotnet run
```

# Test Chat Feature Step-by-step

Sau khi chạy lệnh ```dotnet run``` ở bước trên xong thì đợi 1 chút chương trình sẽ được khởi động tại:

```bash
# Trước tiên là cần đăng nhập
https://localhost:44302/

# Sau đó là truy cập vào trang chat
https://localhost:44302/dms/aichat
```

**Lưu ý: trang web chưa có Sidebar để trỏ tới trang chat, vì vậy hãy truy cập bằng đường link ở trên.** 

**Và hơn hết, trang chat với AI chỉ có thể chat với ChatGPT, Gemini, còn nếu muốn chat với qwen2.5(đây là 1 ollama's model thì phải cài ollama mà Qwen ở local, nếu cần test với AI ở local thì liên hệ tôi để Setting). Trang web cũng chưa có CSS nên xấu lắm!**

---

# Cơ chế AI nhớ ngữ cảnh conversation

## Vấn đề
AI không có memory thực sự giữa các request. Mỗi lần gọi API, AI không biết gì về cuộc trò chuyện trước đó.

## Giải pháp: Redis Conversation Context

### Workflow:
```
1. User gửi tin nhắn → Lấy 10 tin nhắn gần nhất từ Redis
2. Xây dựng context prompt: "Previous conversation: [lịch sử]\n\nUser: [tin nhắn mới]"
3. Gửi toàn bộ context cho AI
4. AI trả lời dựa trên ngữ cảnh đầy đủ
5. Lưu cả user message và AI response vào Redis
```

### Cấu hình:
- **Giới hạn**: 10 tin nhắn gần nhất mỗi conversation
- **Expire**: Tự động xóa sau 2 giờ
- **Storage**: Redis (localhost:6379)
- **Cache Key**: `ConversationContext_{conversationId}`

### Ví dụ:
```
Lần 1:
User: "Tôi tên là Tú"
AI: "Chào Tú!"
→ Lưu Redis: [{role: "user", content: "Tôi tên là Tú"}, {role: "assistant", content: "Chào Tú!"}]

Lần 2:
User: "Bạn có nhớ tên tôi không?"
→ Lấy Redis: [lịch sử 2 tin nhắn trên]
→ Gửi AI: "Previous conversation:\nuser: Tôi tên là Tú\nassistant: Chào Tú!\n\nUser: Bạn có nhớ tên tôi không?"
→ AI: "Có, tên bạn là Tú!"
```

---

**Tài liệu được cập nhật vào lúc: 11h45 ngày 19/11/2025**

**Được viết bởi: Trinhtu34 - Trịnh Ngọc Tú**