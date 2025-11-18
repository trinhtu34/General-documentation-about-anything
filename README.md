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

**Tài liệu được cập nhật vào lúc: 20h15 ngày 18/11/2025**

**Được viết bởi: Trinhtu34 - Trịnh Ngọc Tú**