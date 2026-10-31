# Đưa BC Notes lên Streamlit — không cần SQL

## 1. Tạo nơi lưu bài và PDF

Trên GitHub, tạo repo **Private** tên `MyBlog-data`. Bật **Add a README file** để repo có nhánh `main`.

Repo `MyBlog` chứa code vẫn có thể Public. Repo `MyBlog-data` phải giữ Private vì có cả bài và PDF chưa công khai.

## 2. Tạo token truy cập dữ liệu

Vào GitHub → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.

- Chọn chủ sở hữu tài khoản của bạn.
- Chọn **Only select repositories** → `MyBlog-data`.
- Cấp **Repository permissions → Contents → Read and write**.
- Đặt hạn sử dụng phù hợp và lưu token. Khi token hết hạn, thay token mới trong Streamlit Secrets.

Không đưa token lên repo, không gửi token cho người đọc website.

## 3. Deploy app

Vào https://share.streamlit.io/ → **Create app**:

- Repository: `nguyentonhoaibao98/MyBlog`
- Branch: `main`
- Main file path: `streamlit_app.py`
- Python: `3.12`

Trong **Advanced settings → Secrets**, nhập:

```toml
ADMIN_CODE = "ma-admin-ban-muon-dung"
STORAGE_MODE = "github"
DATA_REPOSITORY = "nguyentonhoaibao98/MyBlog-data"
DATA_BRANCH = "main"
DATA_GITHUB_TOKEN = "token-ban-vua-tao"
```

Thay hai giá trị mã Admin và token bằng giá trị thật. Mã Admin bạn đã yêu cầu trước đó có thể dùng lại tại đây; app Streamlit không tự lấy secret từ website Sites cũ.

Bấm **Deploy**. Trong thiết lập chia sẻ của Streamlit, cho phép mọi người xem app.

## 4. Đăng bài

- Admin nhập mã ở trang đầu.
- Bấm **Create from PDF**.
- Chọn PDF tối đa 20 MB, nhập tiêu đề/mô tả/nội dung.
- Bật **Visible to public visitors** nếu muốn công khai.
- Bấm **Create article**.

Khách chọn **Explore the public library** và chỉ nhìn thấy bài công khai.

## Lưu ý về dữ liệu

Không cần SQL: dữ liệu là JSON và PDF trong repo Private. Nội dung vẫn còn sau khi Streamlit ngủ, reboot hoặc deploy lại.

Không dùng `STORAGE_MODE = "local"` cho nội dung thật trên Streamlit Cloud vì file cục bộ có thể mất. Chế độ này chỉ để thử trên máy.

Xóa bài sẽ bỏ nó khỏi thư viện hiện tại. GitHub vẫn giữ các phiên bản trước trong lịch sử repo Private.

Mã nguồn đã sẵn sàng để deploy; việc tạo repo dữ liệu, cấp token và nhập Secrets phải thực hiện trên tài khoản của bạn. Website Streamlit sẽ có URL riêng sau khi bạn deploy thành công.

