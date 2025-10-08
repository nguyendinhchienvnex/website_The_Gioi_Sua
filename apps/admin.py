from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.shortcuts import redirect
from .models import *
from .models import ProductReport


# ================= Mixin thêm action Edit =================
class EditSelectedMixin:
    def edit_selected(self, request, queryset):
        if queryset.count() == 1:
            obj = queryset.first()
            url = reverse(
                f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change",
                args=[obj.id],
            )
            return redirect(url)
        else:
            self.message_user(request, "Vui lòng chọn 1 bản ghi để sửa.")

    edit_selected.short_description = "Edit selected"
    actions = ["edit_selected"]


# ================= Product =================
@admin.register(Product)
class ProductAdmin(EditSelectedMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "get_price",
        "stock",
        "sold",
        "flash_sale_price",
        "flash_sale_end",
        "get_image",
    )
    list_editable = ("stock", "sold", "flash_sale_price", "flash_sale_end")
    search_fields = ("name",)
    list_filter = ("flash_sale_end",)

    @admin.display(description="Price")
    def get_price(self, obj):
        return f"{obj.price} đ"

    @admin.display(description="Image")
    def get_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px;" />', obj.image.url
            )
        return "No Image"


# ================= Order =================
@admin.register(Order)
class OrderAdmin(EditSelectedMixin, admin.ModelAdmin):
    list_display = ("id", "customer", "complete", "date_order", "transaction_id")


# ================= OrderItem =================
@admin.register(OrderItem)
class OrderItemAdmin(EditSelectedMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "order",
        "get_price",
        "quantity",
        "date_added",
        "get_total",
    )

    @admin.display(description="Total Price")
    def get_total(self, obj):
        return obj.get_total

    @admin.display(description="Price")
    def get_price(self, obj):
        return obj.product.price if obj.product else "N/A"


# ================= Category =================
@admin.register(Category)
class CategoryAdmin(EditSelectedMixin, admin.ModelAdmin):
    list_display = ("id", "name", "is_sub", "slug")


# ================= Review =================
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "customer", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("product__name", "customer__username", "comment")


# ================= ProductReport =================
@admin.register(ProductReport)
class ProductReportAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "customer", "reason", "created_at")
    list_filter = ("reason", "created_at")
    search_fields = ("product__name", "customer__username")
