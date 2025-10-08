from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product
from .models import Review


# Custom widget cho phép multiple files
class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


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


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "price",
            "stock",
            "sold",
            "unit",
            "image",  # ảnh duy nhất
            "category",
            "detail",
            "flash_sale_price",
            "flash_sale_end",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control"}),
            "stock": forms.NumberInput(attrs={"class": "form-control"}),
            "sold": forms.NumberInput(
                attrs={"class": "form-control", "readonly": True}
            ),
            "unit": forms.Select(attrs={"class": "form-select"}),
            "detail": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "category": forms.SelectMultiple(attrs={"class": "form-select"}),
            "image": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),  # ảnh duy nhất
            "flash_sale_price": forms.NumberInput(attrs={"class": "form-control"}),
            "flash_sale_end": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.NumberInput(
                attrs={"min": 1, "max": 5, "class": "form-control"}
            ),
            "comment": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }
        labels = {
            "rating": "Số sao (1-5)",
            "comment": "Bình luận",
        }
