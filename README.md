# Quản Lý Tap Game

Ứng dụng Python để quản lý và điều khiển đồng bộ nhiều instance của game JAR.

## Tính Năng

- ✅ Chọn file JAR để chạy
- ✅ Khởi động nhiều instance game
- ✅ Hiển thị bảng danh sách tất cả instances đang chạy
- ✅ Điều khiển đồng bộ tap cho tất cả instances
- ✅ Dừng từng instance hoặc tất cả
- ✅ Tap thủ công cho từng instance hoặc tất cả

## Cài Đặt

1. Đảm bảo bạn đã cài đặt Python 3.7 trở lên
2. Đảm bảo Java đã được cài đặt và có trong PATH
3. (Tùy chọn) Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

## Sử Dụng

1. Chạy ứng dụng:
```bash
python tap_game_manager.py
```

2. Chọn file JAR bằng nút "Chọn File JAR"
3. Nhập tên instance (tùy chọn) và nhấn "Khởi Động Instance"
4. Bật "Đồng Bộ Tất Cả Tap" để tự động tap tất cả instances
5. Điều chỉnh khoảng thời gian giữa các tap (mặc định: 0.1 giây)

## Lưu Ý

- Ứng dụng sẽ tự động cập nhật trạng thái các instances mỗi giây
- Các instance đã dừng sẽ tự động bị xóa khỏi danh sách
- Để tap thực sự hoạt động, bạn có thể cần tích hợp với pyautogui hoặc API của game

## Tùy Chỉnh Tap Logic

Để thêm logic tap thực tế, bạn có thể chỉnh sửa hàm `send_tap_to_instance()` trong file `tap_game_manager.py`:

```python
def send_tap_to_instance(self, instance_id):
    # Sử dụng pyautogui để click vào cửa sổ game
    # Hoặc gửi command/key event đến process
    pass
```

"# tooldongbo_gamehtth" 
"# tooldongbo_gamehtth" 
"# tooldongbo_gamehtth" 
