from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class MinimumLengthValidator:
    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _(f"Mật khẩu quá ngắn. Cần ít nhất {self.min_length} ký tự."),
                code="password_too_short",
            )

    def get_help_text(self):
        return _(f"Mật khẩu của bạn phải có ít nhất {self.min_length} ký tự.")


class CommonPasswordValidator:
    def validate(self, password, user=None):
        common_passwords = [
            "123456",
            "password",
            "qwerty",
            "abc123",
            "123",
            "abc",
        ]  # ví dụ cơ bản
        if password.lower() in common_passwords:
            raise ValidationError(
                _("Mật khẩu này quá phổ biến, vui lòng chọn mật khẩu khác."),
                code="password_too_common",
            )

    def get_help_text(self):
        return _("Không được dùng mật khẩu quá phổ biến.")


class NumericPasswordValidator:
    def validate(self, password, user=None):
        if password.isdigit():
            raise ValidationError(
                _("Mật khẩu không thể chỉ toàn số."),
                code="password_entirely_numeric",
            )

    def get_help_text(self):
        return _("Mật khẩu không được chỉ toàn số.")
