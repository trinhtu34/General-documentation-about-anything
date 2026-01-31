# ASP.NET ZERO - DPS.DMS Project

## Tài liệu & Tham khảo
- [ASP.NET Zero Development Guide](https://www.aspnetzero.com/Documents/Development-Guide-Core)
- Project này được sử dụng làm template cho các dự án khác

## Thư viện bên thứ 3
- Telerik Reporting 2021 R1 SP2 (v15.0.21.326)
- Telerik Kendo UI 2021 R1 SP2 (v2021.1.330)
- Telerik UI for ASP.NET Core 2021 R1 SP2 (v2021.1.330)

## Kiến trúc dự án (Clean Architecture)

| Tầng | Project | Mô tả |
|------|---------|-------|
| **Domain** | `DPS.Dms.Core` | Entities, Domain Logic |
| **Application** | `DPS.Dms.Application` | Business Logic, Services |
| | `DPS.Dms.Application.Shared` | DTOs, Interfaces |
| **Infrastructure** | `Zero.EntityFrameworkCore` | Database, EF Core |
| **Presentation** | `Zero.Web.Mvc` | Controllers, Views, UI |
| | `Zero.Web.Mvc.Areas.App` | Administrator feature |
| | `Zero.Web.Mvc.Areas.Dms` | Common feature |
| | `Zero.Web.Mvc.wwwroot.view-resources` | JS code |
| | `AppPageNames.cs` | Định nghĩ tên trang |
| | `AppNavigationProvider.cs`n  | Xây dựng menu điều hướng |

## Trước khi chạy dự án thì chạy các lệnh sau 
- đứng tại root folder có chứa file *.sln
```bash
npm install
cd scr/Zero.EntityFrameworkCore
dotnet ef migrations add Add_AIChatTables
dotnet ef database update
cd ..
cd Zero.Web.Mvc
yarn install
npm install gulp-cli -g
gulp buildDev
dotnet run
```

## Workflow tạo tính năng mới

```
1. Entity → 2. Migration → 3. DTO → 4. Mapper → 5. Interface & Service → 6. UI
```

## Hướng dẫn chi tiết: Thêm chức năng "Danh mục"

### Bước 1: Cấu hình Navigation & Permission

#### 1.1 Thêm Page Name
**File**: `AppPageNames.cs`
- Thêm constant vào class `dms`

#### 1.2 Thêm Menu Navigation
**File**: `AppNavigationProvider.cs`
- Thêm menu item vào hàm `MenuCategories()`

#### 1.3 Thêm Localization
**File**: `AbpZero-vi.xml` và `AbpZero.xml`
- Thêm text hiển thị cho menu

#### 1.4 Thêm Permission
**File**: `AppPermissions.cs`
- Thêm permission constants

**File**: `AppAuthorizationProvider.cs`
- Cấu hình permission trong hàm `SetPermissionCategories()`

### Bước 2: Tạo Entity & Migration

#### 2.1 Tạo Entity
**Thư mục**: `customize/Dms/DPS.Dms.Core/Category/`
- Tạo file `[EntityName].cs` (ví dụ: `SectorCategory.cs`)

#### 2.2 Cập nhật DbContext
**File**: `ZeroDbContext.cs`
- Thêm `DbSet<EntityName>` vào DbContext

#### 2.3 Migration Database
```bash
cd Zero.EntityFrameworkCore
dotnet ef migrations add Added_[EntityName]
dotnet ef database update
```

### Bước 3: Tạo DTOs

**Thư mục**: `customize/Dms/DPS.Dms.Application.Shared/Dto/Category/[EntityName]/`

Tạo các DTO sau:

| File | Mục đích |
|------|----------|
| `CreateOrEdit[EntityName]Dto.cs` | Form tạo/sửa |
| `Get[EntityName]ForEditOutput.cs` | Output khi lấy dữ liệu edit |
| `[EntityName]Dto.cs` | Hiển thị dữ liệu |
| `Get[EntityName]ForViewDto.cs` | Hiển thị chi tiết |
| `GetAll[EntityName]Input.cs` | Input cho danh sách |

### Bước 4: Cấu hình AutoMapper

**File**: `CustomAutoMapper.cs` hoặc `CustomDtoMapper.cs`
- Thêm mapping giữa Entity và DTO

### Bước 5: Tạo Application Service

#### 5.1 Interface
**Thư mục**: `customize/Dms/DPS.Dms.Application.Shared/Interface/Category/`
- Tạo `I[EntityName]AppService.cs`

#### 5.2 Implementation
**Thư mục**: `customize/Dms/DPS.Dms.Application/Services/Category/`
- Tạo `[EntityName]AppService.cs`
- Implement business logic (CRUD operations)

### Bước 6: Tạo UI Layer

> **Lưu ý**: 
> - Chức năng DMS → `Areas/Dms`
> - Chức năng quản trị → `Areas/App`

#### 6.1 Controller
**Thư mục**: `Areas/Dms/Controllers/`
- Tạo `[EntityName]Controller.cs`

#### 6.2 ViewModels
**Thư mục**: `Areas/Dms/Models/`
- `[EntityName]ViewModel.cs`
- `CreateOrEdit[EntityName]ModalViewModel.cs`

#### 6.3 Views
**Thư mục**: `Areas/Dms/Views/[EntityName]/`
- `Index.cshtml` - Trang danh sách
- `_CreateOrEditModal.cshtml` - Modal tạo/sửa
- `_ViewDetailModal.cshtml` - Modal xem chi tiết

#### 6.4 JavaScript
**Thư mục**: `wwwroot/view-resources/Areas/Dms/Category/[EntityName]/`
- `Index.js` - Logic trang danh sách
- `_CreateOrEditModal.js` - Logic modal tạo/sửa

## Checklist Implementation

### Core Configuration
- [ ] AppPageNames.cs
- [ ] AppNavigationProvider.cs
- [ ] AppPermissions.cs
- [ ] AppAuthorizationProvider.cs
- [ ] AbpZero.xml / AbpZero-vi.xml
- [ ] ZeroDbContext.cs

### Domain Layer
- [ ] Entity: `DPS.Dms.Core/Category/[EntityName].cs`
- [ ] Migration: `dotnet ef migrations add`
- [ ] Update Database: `dotnet ef database update`

### Application Layer
- [ ] DTOs (5 files)
- [ ] Interface: `I[EntityName]AppService.cs`
- [ ] Service: `[EntityName]AppService.cs`
- [ ] Mapper: `CustomAutoMapper.cs`

### Presentation Layer
- [ ] Controller: `[EntityName]Controller.cs`
- [ ] ViewModels (2 files)
- [ ] Views (3 files)
- [ ] JavaScript (2 files)

## Ví dụ: SectorCategory

### Files đã sửa
- AppPageNames.cs
- AppNavigationProvider.cs
- AbpZero.xml, AbpZero-vi.xml
- AppPermissions.cs
- ZeroDbContext.cs

### Files đã tạo mới

**Domain**
- `customize/Dms/DPS.Dms.Core/Category/SectorCategory.cs`

**Application**
- `customize/Dms/DPS.Dms.Application.Shared/Dto/Category/SectorCategory/`
  - CreateOrEditSectorCategoryDto.cs
  - GetSectorCategoryForEditOutput.cs
  - SectorCategoryDto.cs
  - GetSectorCategoryForViewDto.cs
  - GetAllSectorCategoriesInput.cs
- `customize/Dms/DPS.Dms.Application.Shared/Interface/Category/ISectorCategoryAppService.cs`
- `customize/Dms/DPS.Dms.Application/Services/Category/SectorCategoryAppService.cs`

**Presentation**
- Controllers, ViewModels, Views, JavaScript (theo cấu trúc ở Bước 6)

## Tips & Best Practices

- Luôn chạy migration sau khi tạo/sửa entity
- Đặt tên file và class theo convention của project
- Test từng bước trước khi chuyển sang bước tiếp theo
- Sử dụng permission để kiểm soát quyền truy cập
- Localization cho cả tiếng Việt và tiếng Anh
