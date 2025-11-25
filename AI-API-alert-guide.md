# Hướng dẫn cấu hình Alert cho API của ChatGPT và Gemini 

## ChatGPT - OpenAI

Để cấu hình Budget Alert cho ChatGPT API key, vui lòng làm theo các bước sau :
+ Truy cập vào trang : Usage của OpenAI [Tại Đây](https://platform.openai.com/usage)
![ChatGPT Usage Page](/images/img-1-chatgpt.png)
+ Tiếp theo ấn vào **Edit budget**
![Edit Budget](/images/img-2-chatgpt.png)
+ Tiếp theo bạn hãy ấn vào **Add alert**
![Add Alert](/images/img-3-chatgpt.png)
+ Tiếp tục nhập vào mốc Budget cần cảnh báo - Tiêu đề khi nhận email - Email nhận thông báo
![Configure Alert](/images/img-4-chatgpt.png)
+ Cuối cùng là ấn **Add alert**
![Confirm Alert](/images/img-5-chatgpt.png)

## Gemini - Google AI Studio - Google Cloud Platform

Để cấu hình Budget Alert cho Gemini API Key bạn cần truy cập vào dịch vụ Billing của Google Cloud Platform ( GCP ), vui lòng làm theo các bước sau : 
+ Truy cập vào tài khoản Google AI Studio : [Tại Đây](https://aistudio.google.com)
+ Ấn vào **Usage and Billing**
![Usage and Billing](/images/img-1-gcp.png)
+ Tiếp theo ấn vào **Billing**
![Billing](/images/img-2-gcp.png)
+ Tiếp theo ấn vào **Open in Cloud Console**
![Open in Cloud Console](/images/img-3-gcp.png)
+ Tiếp theo cần chọn project đang sử dụng Gemini API Key
![Select Project](/images/img-4-gcp.png)
+ Tiêp theo chọn project mà bạn đang dùng cho Gemini API Key
![Choose Project](/images/img-5-gcp.png)
+ Ấn vào **Go to linked billing account**
![Go to Billing Account](/images/img-6-gcp.png)
+ Ấn vào Budgets and alerts
![Budgets and Alerts](/images/img-7-gcp.png)
+ Ấn vào Create Budget
![Create Budget](/images/img-8-gcp.png)
+ Nhập vào các trường dữ liệu như **Name** sau đó kéo xuống ấn **Finish**
![Enter Budget Name](/images/img-9-gcp.png)
+ Nhập vào số tiền mà bạn chỉ định và sau đó ấn **Next**
![Set Budget Amount](/images/img-10-gcp.png)
+ Tại mục **Set alert threshold rules** bạn cần chỉ định khi số tiền sử dụng thực tế đến bao nhiêu % là sẽ gửi cảnh báo
![Set Alert Threshold](/images/img-11-gcp.png)
+ Ở phần **Manage notifications** bạn cần chỉ định Alert sẽ gửi về đâu, bạn ấn tích vào lựa chọn **Link Monitoring email notification channels to this budget** và ấn **Select a project**
![Manage Notifications](/images/img-12-gcp.png)
+ Chọn vào Project mà đang sử dụng Gemini API Key
![Select Project for Notifications](/images/img-13-gcp.png)
+ Tiếp theo cần chọn là kênh nào sẽ nhận thông báo, ở đây cần ấn vào **Notification Channels** và ấn vào **Manage Notification Channels**
![Notification Channels](/images/img-14-gcp.png)
+ Tiếp theo ấn vào **Add new**
![Add New Channel](/images/img-15-gcp.png)
+ Nhập vào địa chỉ email mà bạn muốn nhận thông báo và nhập vào tên hiển thị và ấn **Save**
![Enter Email](/images/img-16-gcp.png)
+ Quay ra giao diện Notification Channels chọn vào Tên mà bạn vừa thêm
![Select Channel](/images/img-17-gcp.png)
+ Cuối cùng là ấn **Finish** để hoàn thành quá trình set Budget Alert cho việc sử dụng Gemini API key thông qua việc sử dụng dịch vụ Google Billing của GCP.
![Finish Setup](/images/img-18-gcp.png)