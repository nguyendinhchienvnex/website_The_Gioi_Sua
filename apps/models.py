from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone


class Category(models.Model):
    sub_category = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="sub_categories",
        null=True,
        blank=True,
    )
    is_sub = models.BooleanField(default=False)
    name = models.CharField(max_length=255, null=True)
    slug = models.SlugField(max_length=255, unique=True)

    def __str__(self):
        return self.name


# Thay đổi form register
class CreateUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        ]


User = get_user_model()


class ChangeUserProfileForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    password_confirmation = forms.CharField(widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def clean_password_confirmation(self):
        password = self.cleaned_data.get("password")
        password_confirmation = self.cleaned_data.get("password_confirmation")

        if password and password != password_confirmation:
            raise forms.ValidationError("Passwords do not match.")

        return password_confirmation

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")

        if password:
            user.set_password(password)

        if commit:
            user.save()

        return user


from django.db import models
from django.utils import timezone
from django.db.models import Sum


from django.db import models
from django.utils import timezone
from django.db.models import Sum


from django.db import models
from django.utils import timezone
from django.db.models import Sum


class Product(models.Model):
    UNIT_CHOICES = [
        ("piece", "Hộp"),
        ("box", "Thùng"),
    ]

    category = models.ManyToManyField("Category", related_name="product")
    name = models.CharField(max_length=255, null=True)
    price = models.FloatField(default=0, null=True, blank=False)
    digital = models.BooleanField(default=False, null=True, blank=False)
    image = models.ImageField(null=True, blank=True)
    detail = models.TextField(null=True, blank=True)

    stock = models.IntegerField(default=0)  # tổng số hàng nhập
    sold = models.IntegerField(default=0)  # giữ lại cho tương thích

    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="piece")

    flash_sale_price = models.FloatField(null=True, blank=True)
    flash_sale_end = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name if self.name else "Unnamed Product"

    # ✅ Lấy URL ảnh chính
    @property
    def ImageURL(self):
        try:
            return self.image.url
        except Exception:
            return ""

    # ✅ Trung bình rating
    @property
    def avg_rating(self):
        return self.reviews.aggregate(models.Avg("rating"))["rating__avg"] or 5

    # ✅ Số lượt đánh giá
    @property
    def review_count(self):
        return self.reviews.count()

    # ✅ Kiểm tra có đang flash sale không
    @property
    def is_flash_sale(self):
        return self.flash_sale_end and self.flash_sale_end > timezone.now()

    # ✅ Tính số đã bán dựa trên OrderItem (chỉ tính đơn complete)
    @property
    def sold_count(self):
        total = self.order_items.filter(order__complete=True).aggregate(
            total=Sum("quantity")
        )["total"]
        return total or 0

    # ✅ Tính số còn lại
    @property
    def remaining_stock(self):
        return max(self.stock - self.sold_count, 0)

    # ✅ Giá hiển thị (theo đơn vị)
    @property
    def display_price(self):
        if self.unit == "box":  # nếu là Thùng
            return self.price * 30
        return self.price


class Order(models.Model):
    STATUS_CHOICES = [
        ("confirmed", "Đã xác nhận"),
        ("shipping", "Đang giao hàng"),
        ("delivered", "Đã giao hàng"),
        ("completed", "Hoàn tất"),
        ("cancelled", "Đã hủy"),
    ]

    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_order = models.DateTimeField(auto_now_add=True)
    complete = models.BooleanField(default=False, null=True, blank=False)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)

    # 🔹 Trạng thái đơn hàng
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="confirmed"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"Order #{self.id} - {self.customer.username if self.customer else 'Guest'}"
        )

    # ✅ Tính tổng số lượng item trong giỏ
    @property
    def get_cart_items(self):
        if not self.pk:
            return 0
        orderitems = (
            self.order_items.all()
        )  # 🔹 dùng related_name thay cho orderitem_set
        return sum(
            item.quantity if item and item.quantity else 0 for item in orderitems
        )

    # ✅ Tính tổng tiền giỏ hàng (có Flash Sale + đơn vị hộp/thùng)
    @property
    def get_cart_total(self):
        if not self.pk:
            return 0
        orderitems = self.order_items.all()  # 🔹 đổi sang order_items
        return sum(item.get_total if item else 0 for item in orderitems)

    # ✅ Kiểm tra đơn hàng còn hoạt động
    @property
    def is_active(self):
        return self.status not in ["completed", "cancelled"]

    # ✅ Hiển thị badge màu cho UI
    def get_status_badge(self):
        colors = {
            "confirmed": "warning",  # vàng
            "shipping": "info",  # xanh dương nhạt
            "delivered": "primary",  # xanh dương
            "completed": "success",  # xanh lá
            "cancelled": "danger",  # đỏ
        }
        return colors.get(self.status, "secondary")

    # ✅ Đồng bộ complete với status + tránh đơn rác 0đ
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)  # lưu lần đầu để có ID

        if not is_new:  # xử lý sau khi có ID
            if self.get_cart_total == 0:
                # Đơn rác: hủy luôn, không giữ pending
                self.complete = False
                self.status = "cancelled"
            elif self.status == "completed":
                # Hoàn tất => complete = True
                self.complete = True

            # Update lại nếu có thay đổi
            super().save(update_fields=["complete", "status"])


class OrderItem(models.Model):
    product = models.ForeignKey(
        Product,
        related_name="order_items",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    order = models.ForeignKey(
        Order,
        related_name="order_items",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    quantity = models.IntegerField(default=0, null=True, blank=False)
    date_added = models.DateTimeField(auto_now_add=True)

    # ✅ Lưu đơn vị người mua chọn (theo Product.UNIT_CHOICES: piece/hộp, box/thùng)
    unit = models.CharField(
        max_length=10,
        choices=Product.UNIT_CHOICES,
        default="piece",
    )

    # ✅ Tính tổng tiền từng dòng
    @property
    def get_total(self):
        if not self.product:
            return 0

        # Giá cơ bản (ưu tiên flash sale nếu có)
        if self.product.is_flash_sale and self.product.flash_sale_price:
            base_price = self.product.flash_sale_price
        else:
            base_price = self.product.price or 0

        # Nếu khách chọn Thùng (box) thì giá = 30 hộp
        if self.unit == "box":
            base_price *= 30

        return base_price * (self.quantity or 0)

    def __str__(self):
        order_id = self.order.id if self.order else "N/A"
        product_name = self.product.name if self.product else "No product"
        unit_display = dict(Product.UNIT_CHOICES).get(self.unit, self.unit)
        return f"Order #{order_id} - {product_name} ({unit_display}) x{self.quantity}"


# class InformationCustomer(models.Model):
#     customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
#     order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
#     address = models.CharField(max_length=255, null=True)
#     city = models.CharField(max_length=255, null=True)
#     phone = models.CharField(max_length=255, null=True)
#     state = models.CharField(max_length=255, null=True)
#     date_added = models.DateTimeField(auto_now_add=True)
#
#     def __str__(self):
#         return self.address


class Payment_VNPay(models.Model):
    order_id = models.IntegerField(default=0, null=True, blank=True)
    amount = models.FloatField(default=0.0, null=True, blank=True)
    order_desc = models.CharField(max_length=200, null=True, blank=True)
    vnp_TransactionNo = models.CharField(max_length=200, null=True, blank=True)
    vnp_ResponseCode = models.CharField(max_length=200, null=True, blank=True)

    # log thời gian
    created_at = models.DateTimeField(auto_now_add=True)  # chỉ set khi tạo record
    updated_at = models.DateTimeField(auto_now=True)  # update mỗi lần save()

    def __str__(self):
        return f"Payment {self.order_id} - {self.amount} VND"


class PaymentForm(forms.Form):
    order_type = forms.CharField(max_length=20)
    amount = forms.IntegerField()
    order_desc = forms.CharField(max_length=100)
    bank_code = forms.CharField(max_length=20, required=False)
    language = forms.CharField(max_length=2)


# ⭐ Đánh giá sản phẩm
class Review(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, null=True, blank=True
    )  # ✅ cho phép null
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5)  # 1-5 sao
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review {self.rating}★ - {self.product.name}"


class ProductReport(models.Model):
    REPORT_CHOICES = [
        ("fake", "Hàng giả / nhái"),
        ("expired", "Hết hạn sử dụng"),
        ("wrong", "Sai thông tin"),
        ("other", "Khác"),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reports"
    )
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.CharField(max_length=50, choices=REPORT_CHOICES, default="other")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report {self.product.name} - {self.reason}"


# ⭐ Địa chỉ người dùng
from django.db import models
from django.contrib.auth.models import User


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)

    # Tách địa chỉ chi tiết
    province = models.CharField("Tỉnh/Thành phố", max_length=100, blank=True, null=True)
    district = models.CharField("Quận/Huyện", max_length=100, blank=True, null=True)
    ward = models.CharField("Phường/Xã", max_length=100, blank=True, null=True)
    detail = models.CharField("Số nhà, đường...", max_length=255, blank=True, null=True)

    # Trường tổng hợp
    address_line = models.CharField("Địa chỉ đầy đủ", max_length=255, blank=True)

    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Build lại address_line khi lưu
        parts = [self.detail, self.ward, self.district, self.province]
        self.address_line = ", ".join([p for p in parts if p])

        # Nếu chọn mặc định -> bỏ mặc định ở các địa chỉ khác
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(
                pk=self.pk
            ).update(is_default=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.address_line or 'Chưa có địa chỉ đầy đủ'}"


class Voucher(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percent = models.IntegerField(default=0)  # 10, 20...
    free_ship = models.BooleanField(default=False)
    expire_date = models.DateTimeField()

    def is_valid(self):
        from django.utils import timezone

        return self.expire_date >= timezone.now()
