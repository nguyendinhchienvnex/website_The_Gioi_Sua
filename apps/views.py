from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import loader
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated

from .models import *
import json
from django.contrib.auth.forms import (
    UserCreationForm,
    UserChangeForm,
    PasswordChangeForm,
)
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
import random
import string
from django.core.mail import send_mail

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.urls import reverse
from .serializers import OrderItemSerializer, ProductSerializer, CategorySerializer
from django.contrib.auth.decorators import login_required, user_passes_test

import hashlib
import hmac
import json
import random
import requests
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from urllib.parse import quote

from apps.models import PaymentForm
from apps.vnpay import vnpay

from django.core.cache import cache
from datetime import timedelta
from django.utils import timezone

from django.db.models import Sum, Count, F
import calendar
from django.utils.timezone import now
from django import forms
from .models import OrderItem, Payment_VNPay

from django.core.mail import send_mail
from .forms import ProductForm, ReviewForm
from datetime import date, timedelta


@api_view(["GET", "POST", "PUT", "DELETE"])
def register_api(request, user_id=None):
    if request.method == "GET":
        if user_id:
            user = get_object_or_404(User, pk=user_id)
            user_data = {
                "id": user.id,
                "username": user.username,
                "password": user.password,
                "email": user.email,
            }
            return Response({"user": user_data}, status=status.HTTP_200_OK)
        else:
            users = User.objects.all()
            user_data = [
                {
                    "id": user.id,
                    "username": user.username,
                    "password": user.password,
                    "email": user.email,
                }
                for user in users
            ]
            return Response({"users": user_data}, status=status.HTTP_200_OK)

    # Xử lý POST request
    elif request.method == "POST":
        form = UserCreationForm(request.data)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get("username")
            response_data = {
                "username": username,
                "message": "Register successful",
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        errors = form.errors.get_json_data()
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    # Xử lý PUT request (Sửa thông tin người dùng)
    elif request.method == "PUT":
        user = get_object_or_404(User, pk=user_id)
        try:
            # Chuyển đổi dữ liệu từ chuỗi JSON sang dict
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return Response(
                {"error": "Invalid JSON data"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Sử dụng UserChangeForm để xử lý cập nhật thông tin người dùng
        form = UserChangeForm(data, instance=user)

        if form.is_valid():
            form.save()
            return Response(
                {"message": "User updated successfully"}, status=status.HTTP_200_OK
            )

        return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)
    # Xử lý DELETE request (Xóa người dùng)
    elif request.method == "DELETE":
        user = get_object_or_404(User, pk=user_id)
        user.delete()
        return Response(
            {"message": "User deleted successfully"}, status=status.HTTP_204_NO_CONTENT
        )

    return Response(
        {"error": "Method Not Allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])  # Đảm bảo chỉ cho phép người dùng đã đăng nhập
def userId_api(request):
    if request.method == "GET":
        # Lấy thông tin người dùng hiện tại
        user = request.user
        return Response({"id": user.id}, status=status.HTTP_200_OK)


def register(request):
    order = {"get_cart_items": 0, "get_cart_total": 0}
    cartItems = order["get_cart_items"]
    form = CreateUserForm()

    if request.method == "POST":
        form = CreateUserForm(request.POST)
        if form.is_valid():
            # Lấy dữ liệu từ form
            username = form.cleaned_data.get("username")
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password1")
            first_name = form.cleaned_data.get("first_name")
            last_name = form.cleaned_data.get("last_name")

            # Sinh OTP
            otp = str(random.randint(100000, 999999))

            # Lưu tạm vào session
            request.session["register_data"] = {
                "username": username,
                "email": email,
                "password": password,
                "first_name": first_name,
                "last_name": last_name,
                "otp": otp,
            }

            # Gửi OTP về Gmail
            send_mail(
                "🎉 Xác thực tài khoản tại Thế Giới Sữa",
                f"""
                    Xin chào {username},

                    Cảm ơn bạn đã đăng ký tài khoản tại **Thế Giới Sữa**.
                    Mã OTP xác thực của bạn là: **{otp}**

                    👉 Vui lòng nhập mã OTP này trong vòng 5 phút để hoàn tất đăng ký.

                    Nếu bạn không yêu cầu đăng ký, vui lòng bỏ qua email này.

                    Thân mến,
                    Đội ngũ hỗ trợ Thế Giới Sữa 🍼
                """,
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )

            # Chuyển sang trang nhập OTP
            return redirect("verify_otp")

    context = {
        "form": form,
        "user_login": "hidden",
        "cartItems": cartItems,
    }
    return render(request, "app/register.html", context)


def verify_otp(request):
    if request.method == "POST":
        otp_input = request.POST.get("otp")
        data = request.session.get("register_data")

        if data and otp_input == data["otp"]:
            # Tạo user sau khi xác thực OTP
            user = User.objects.create_user(
                username=data["username"],
                email=data["email"],
                password=data["password"],
                first_name=data["first_name"],
                last_name=data["last_name"],
            )
            del request.session["register_data"]  # Xoá session
            messages.success(
                request, "🎉 Bạn đã đăng ký thành công! Hãy đăng nhập để tiếp tục."
            )
            return redirect("login")
        else:
            return render(request, "app/verify_otp.html", {"error": "OTP không đúng!"})

    return render(request, "app/verify_otp.html")


def change_account(request):
    if request.user.is_authenticated:
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.order_items.all()
        cartItems = order.get_cart_items
        user_not_login = "hidden"
        user_login = "show"

    categories = Category.objects.filter(is_sub=False)

    if request.method == "POST":
        form = ChangeUserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()

            # Gửi mail thông báo đổi mật khẩu
            subject = "Xác nhận thay đổi mật khẩu"
            message = f"Xin chào {user.username},\n\nBạn vừa thay đổi mật khẩu thành công cho tài khoản {user.email}.\n\nNếu đây không phải là bạn, hãy liên hệ ngay với quản trị viên."
            recipient_list = [user.email]

            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)

            return redirect("login")  # hoặc redirect về profile
    else:
        form = ChangeUserProfileForm(instance=request.user)

    context = {
        "form": form,
        "cartItems": cartItems,
        "user_not_login": user_not_login,
        "user_login": user_login,
        "categories": categories,
    }
    return render(request, "app/change_account.html", context)


def login_account(request):
    if request.user.is_authenticated:
        return redirect("home")

    items = []
    order = {"get_cart_items": 0, "get_cart_total": 0}
    cartItems = order["get_cart_items"]
    categories = Category.objects.filter(is_sub=False)

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Khóa login theo username (có thể đổi sang IP: request.META.get('REMOTE_ADDR'))
        cache_key = f"login_attempts_{username}"
        attempts = cache.get(cache_key, {"count": 0, "blocked_until": None})

        # Nếu đang bị khóa
        if attempts["blocked_until"] and attempts["blocked_until"] > timezone.now():
            remaining = (attempts["blocked_until"] - timezone.now()).seconds // 60 + 1
            messages.error(
                request,
                f"Tài khoản này đã bị khóa, vui lòng thử lại sau {remaining} phút.",
            )
            return render(
                request,
                "app/login.html",
                {
                    "user_login": "hidden",
                    "categories": categories,
                    "cartItems": cartItems,
                },
            )

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Reset lại số lần sai nếu login thành công
            cache.delete(cache_key)
            messages.success(request, "Bạn đã đăng nhập thành công!")
            return redirect("home")

        elif username == "admin" and password == "admin":
            return render(request, "app/admin.html")

        else:
            # Sai mật khẩu → tăng số lần đếm
            attempts["count"] += 1

            if attempts["count"] >= 5:
                # Khóa 10 phút
                attempts["blocked_until"] = timezone.now() + timedelta(minutes=10)
                messages.error(
                    request, "Bạn đã nhập sai quá 5 lần. Tài khoản bị khóa 10 phút."
                )
            else:
                messages.error(
                    request,
                    f"Tài khoản hoặc mật khẩu không chính xác! (Sai {attempts['count']} lần)",
                )

            # Lưu lại cache (timeout 10 phút để tự reset)
            cache.set(cache_key, attempts, timeout=600)

    return render(
        request,
        "app/login.html",
        {
            "user_login": "hidden",
            "categories": categories,
            "cartItems": cartItems,
        },
    )


def logout_account(request):
    # Xủ lí thoát
    logout(request)
    return redirect("login")


def profile(request):
    form = CreateUserForm()
    user_not_login = "hidden"
    user_login = "show"
    shipping_time = None

    if request.user.is_authenticated:
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.order_items.all()
        cartItems = order.get_cart_items

        user_address = ""
        user_phone = ""

        if request.method == "POST":
            user_address = request.POST.get("address", "")
            user_phone = request.POST.get("phone", "")
            shipping_time = estimate_shipping(user_address)

        user_info = {
            "username": customer.username,
            "email": customer.email,
            "password": customer.password,
            "address": user_address,
            "phone": user_phone,
        }
    else:
        items = []
        order = {"get_cart_items": 0, "get_cart_total": 0}
        cartItems = order["get_cart_items"]
        user_info = None
        user_not_login = "show"
        user_login = "hidden"

    categories = Category.objects.filter(is_sub=False)
    active_category = request.GET.get("category", "")
    products = Product.objects.all()

    context = {
        "form": form,
        "products": products,
        "cartItems": cartItems,
        "user_not_login": user_not_login,
        "user_login": user_login,
        "categories": categories,
        "user_info": user_info,
        "shipping_time": shipping_time,
    }

    return render(request, "app/profile.html", context)


@csrf_exempt
@api_view(["GET", "POST", "PUT", "DELETE"])
def product_api(request):
    if request.method == "GET":
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "PUT":
        try:
            product = Product.objects.get(pk=request.data["id"])
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        try:
            product = Product.objects.get(pk=request.data["id"])
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND
            )

        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def home(request):
    if request.user.is_authenticated:
        customer = request.user

        # Lấy tất cả giỏ chưa hoàn tất
        orders = Order.objects.filter(customer=customer, complete=False).order_by(
            "-date_order"
        )

        order = None
        if orders.exists():
            # Giữ lại giỏ mới nhất
            order = orders.first()
            # Xóa giỏ rác còn lại
            if orders.count() > 1:
                orders.exclude(id=order.id).delete()

            # Nếu giỏ rỗng thì hủy luôn
            if order.get_cart_total == 0:
                order.delete()
                order = None

        # Nếu còn giỏ hợp lệ
        if order:
            items = order.order_items.all()
            cartItems = order.get_cart_items
        else:
            items, cartItems = [], 0

        user_not_login, user_login = "hidden", "show"

    else:
        items, order, cartItems = [], None, 0
        user_not_login, user_login = "show", "hidden"

    categories = Category.objects.filter(is_sub=False)

    # Lọc sản phẩm theo category (nếu có chọn)
    active_category = request.GET.get("category", "")
    products = Product.objects.all()
    if active_category:
        products = products.filter(category__slug=active_category)

    context = {
        "products": products,
        "cartItems": cartItems,
        "user_not_login": user_not_login,
        "user_login": user_login,
        "categories": categories,
        "current": "home",
        "now": now(),
    }
    return render(request, "app/home.html", context)


def cart(request):
    if request.user.is_authenticated:
        customer = request.user

        # Lấy tất cả giỏ chưa hoàn tất
        orders = Order.objects.filter(customer=customer, complete=False).order_by(
            "-date_order"
        )

        order = None
        if orders.exists():
            # Giữ lại giỏ hàng mới nhất
            order = orders.first()
            # Xóa giỏ rác còn lại (nếu có nhiều)
            if orders.count() > 1:
                orders.exclude(id=order.id).delete()

            # Nếu giỏ rác hoặc giỏ trống thì bỏ qua
            if order.get_cart_total == 0:
                order.delete()
                order = None

        # Nếu còn order hợp lệ
        if order:
            items = order.order_items.all()
            cartItems = order.get_cart_items
        else:
            items, cartItems = [], 0

        user_not_login, user_login = "hidden", "show"

    else:
        items, order, cartItems = [], None, 0
        user_not_login, user_login = "show", "hidden"

    categories = Category.objects.filter(is_sub=False)
    context = {
        "items": items,
        "order": order,
        "cartItems": cartItems,
        "user_not_login": user_not_login,
        "user_login": user_login,
        "categories": categories,
        "current": "cart",
    }
    return render(request, "app/cart.html", context)


@api_view(["GET", "POST", "PUT", "DELETE"])
def cart_api(request, user_id, item_id=None):
    try:
        customer = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        # Trả về thông tin về sản phẩm trong giỏ hàng
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.order_items.all()
        serializer = OrderItemSerializer(items, many=True)
        total_price = (
            order.get_cart_total
        )  # Sử dụng phương thức để tính tổng tiền giỏ hàng
        return Response(
            {"items": serializer.data, "total_price_all": total_price},
            status=status.HTTP_200_OK,
        )

    elif request.method == "POST":
        # Xử lý thêm sản phẩm vào giỏ hàng
        serializer = OrderItemSerializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data["product"]
            quantity = serializer.validated_data["quantity"]

            # Kiểm tra xem sản phẩm đã có trong giỏ hàng chưa
            order, created = Order.objects.get_or_create(
                customer=customer, complete=False
            )
            order_item, created = OrderItem.objects.get_or_create(
                order=order, product_id=product_id
            )
            # Cập nhật số lượng
            order_item.quantity += quantity
            order_item.save()

            return Response(
                {"message": "Product added to cart successfully"},
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "PUT":
        # Cập nhật sản phẩm trong giỏ hàng
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        try:
            item = order.order_items.get(id=item_id)
        except OrderItem.DoesNotExist:
            return Response(
                {"error": "Order item not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = OrderItemSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Order item updated successfully"},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        # Xóa sản phẩm khỏi giỏ hàng
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        try:
            item = order.order_items.get(id=item_id)
        except OrderItem.DoesNotExist:
            return Response(
                {"error": "Order item not found"}, status=status.HTTP_404_NOT_FOUND
            )
        item.delete()
        return Response(
            {"message": "Order item deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )


@login_required
def checkout(request):
    customer = request.user
    order = Order.objects.filter(customer=customer, complete=False).first()

    if order and order.get_cart_total > 0:
        items = order.order_items.all()
        cartItems = order.get_cart_items
    else:
        order, items, cartItems = None, [], 0

    user_not_login, user_login = "hidden", "show"
    categories = Category.objects.filter(is_sub=False)

    # ==== Địa chỉ giao hàng ====
    addresses = Address.objects.filter(user=customer)

    # ==== Voucher / Free ship ====
    discount = 0
    free_ship = False
    voucher_code = request.GET.get("voucher")

    if voucher_code:
        try:
            voucher = Voucher.objects.get(code=voucher_code)
            if voucher.is_valid():
                discount = voucher.discount_percent
                free_ship = voucher.free_ship
        except Voucher.DoesNotExist:
            pass

    # ==== Tính tổng ====
    total = order.get_cart_total if order else 0
    if discount > 0:
        total = total - total * discount / 100
    shipping_fee = 0 if free_ship else 30000  # mặc định 30k ship
    grand_total = total + shipping_fee

    # ==== Ngày giao hàng dự kiến ====
    eta = date.today() + timedelta(days=3)  # ví dụ 3 ngày sau

    context = {
        "items": items,
        "order": order,
        "cartItems": cartItems,
        "user_not_login": user_not_login,
        "user_login": user_login,
        "categories": categories,
        "addresses": addresses,
        "discount": discount,
        "free_ship": free_ship,
        "grand_total": grand_total,
        "eta": eta,
    }
    return render(request, "app/checkout.html", context)


def updateItem(request):
    data = json.loads(request.body)
    productId = data["productId"]
    action = data["action"]
    unit = data.get("unit", "piece")  # ✅ lấy đơn vị
    quantity = int(data.get("quantity", 1))  # ✅ lấy số lượng

    customer = request.user
    product = Product.objects.get(id=productId)

    order, created = Order.objects.get_or_create(customer=customer, complete=False)
    orderItem, created = OrderItem.objects.get_or_create(
        order=order, product=product, unit=unit  # ✅ unit theo lựa chọn
    )

    if action == "add":
        orderItem.quantity += quantity
    elif action == "remove":
        orderItem.quantity -= 1

    orderItem.save()

    if orderItem.quantity <= 0:
        orderItem.delete()

    return JsonResponse("Item was updated", safe=False)


def search(request):
    if request.method == "POST":
        searched = request.POST["searched"]
        keys = Product.objects.filter(name__contains=searched)
    if request.user.is_authenticated:
        customer = request.user
        # Lấy và tạo order
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        # Truy cập all đơn hàng đã đặt
        items = order.order_items.all()
        cartItems = order.get_cart_items
        user_not_login = "hidden"
        user_login = "show"
        categories = Category.objects.filter(is_sub=False)
    else:
        items = []
        order = {"get_cart_items": 0, "get_cart_total": 0}
        cartItems = order["get_cart_items"]
        user_not_login = "show"
        user_login = "hidden"
        # Lấy all sản phầm
    products = Product.objects.all()
    context = {
        "products": products,
        "cartItems": cartItems,
        "user_not_login": user_not_login,
        "user_login": user_login,
        "searched": searched,
        "keys": keys,
        "categories": categories,
    }

    return render(request, "app/search.html", context)


def category(request):
    categories = Category.objects.filter(is_sub=False)  # Khai báo biến categories
    active_category_slug = request.GET.get("category", "")
    active_category = None
    products = Product.objects.all()  # Giá trị mặc định
    if active_category_slug:
        try:
            active_category = Category.objects.get(slug=active_category_slug)
            products = Product.objects.filter(category=active_category)
        except Category.DoesNotExist:
            active_category = None
    if request.user.is_authenticated:
        customer = request.user
        # Lấy và tạo order
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        # Truy cập all đơn hàng đã đặt
        items = order.order_items.all()
        cartItems = order.get_cart_items
        user_not_login = "hidden"
        user_login = "show"
        # Ng dùng chọn
        active_category = request.GET.get("category", "")
        if active_category:
            products = Product.objects.filter(category__slug=active_category)
    else:
        items = []
        order = {"get_cart_items": 0, "get_cart_total": 0}
        cartItems = order["get_cart_items"]
        user_not_login = "show"
        user_login = "hidden"
    # Ng dùng chọn
    active_category = request.GET.get("category", "")
    context = {
        "items": items,
        "order": order,
        "cartItems": cartItems,
        "user_not_login": user_not_login,
        "user_login": user_login,
        "categories": categories,
        "products": products,
        "active_category": active_category,
        "current": "product",
        "now": now(),  # để so sánh flash_sale_end trong template
    }
    return render(request, "app/category.html", context)


@csrf_exempt
@api_view(["GET", "POST", "PUT", "DELETE"])
def category_api(request, pk=None):
    if request.method == "GET":
        if pk:
            # Lấy thông tin category theo id
            try:
                category = Category.objects.get(pk=pk)
                serializer = CategorySerializer(category)
                return Response(serializer.data)
            except Category.DoesNotExist:
                return Response(
                    {"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Lấy danh sách category
            categories = Category.objects.filter(is_sub=False)
            serializer = CategorySerializer(categories, many=True)
            return Response(serializer.data)

    elif request.method == "POST":
        # Tạo một category mới
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "PUT":
        # Cập nhật thông tin category
        try:
            category = Category.objects.get(pk=pk)
            serializer = CategorySerializer(category, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Category.DoesNotExist:
            return Response(
                {"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND
            )

    elif request.method == "DELETE":
        # Xóa một category
        try:
            category = Category.objects.get(pk=pk)
            category.delete()
            return Response(
                {"message": "Category deleted successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Category.DoesNotExist:
            return Response(
                {"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND
            )


def detail(request):
    if request.user.is_authenticated:
        customer = request.user
        # Lấy hoặc tạo giỏ hàng chưa hoàn tất
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.order_items.all()
        cartItems = order.get_cart_items
        user_not_login = "hidden"
        user_login = "show"
    else:
        items = []
        order = {"get_cart_items": 0, "get_cart_total": 0}
        cartItems = order["get_cart_items"]
        user_not_login = "show"
        user_login = "hidden"

    # Lấy sản phẩm theo id (bắt buộc phải tồn tại, nếu không -> 404)
    product_id = request.GET.get("id")
    product = get_object_or_404(Product, id=product_id) if product_id else None

    categories = Category.objects.filter(is_sub=False)

    # 👉 Ước tính vận chuyển
    shipping_estimate = "3 - 5 ngày"
    if request.user.is_authenticated and hasattr(request.user, "profile"):
        try:
            shipping_estimate = estimate_shipping(request.user.profile.address)
        except:
            pass

    reviews = (
        product.reviews.select_related("customer").order_by("-created_at")
        if product
        else []
    )

    # ✅ Truyền thêm dữ liệu số lượng đã bán và còn lại
    sold_count = product.sold_count if product else 0
    remaining_stock = product.remaining_stock if product else 0

    context = {
        "items": items,
        "order": order,
        "cartItems": cartItems,
        "user_not_login": user_not_login,
        "user_login": user_login,
        "categories": categories,
        "product": product,  # sản phẩm chi tiết
        "shipping_estimate": shipping_estimate,
        "now": timezone.now(),  # để so sánh flash_sale_end trong template
        "reviews": reviews,  # đánh giá sản phẩm
        "sold_count": sold_count,  # ✅ số lượng đã bán (chuẩn theo OrderItem complete)
        "remaining_stock": remaining_stock,  # ✅ số lượng còn lại
    }
    return render(request, "app/detail.html", context)


def hotline(request):
    if request.user.is_authenticated:
        customer = request.user
        # Lấy và tạo order
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        # Truy cập all đơn hàng đã đặt
        items = order.order_items.all()
        cartItems = order.get_cart_items
        user_not_login = "hidden"
        user_login = "show"
        categories = Category.objects.filter(is_sub=False)
    else:
        items = []
        order = {"get_cart_items": 0, "get_cart_total": 0}
        cartItems = order["get_cart_items"]
        # Ân đăng nhập và đăng kí
        user_not_login = "show"
        user_login = "hidden"
        categories = Category.objects.filter(is_sub=False)

    context = {
        "items": items,
        "order": order,
        "cartItems": cartItems,
        "user_not_login": user_not_login,
        "user_login": user_login,
        "categories": categories,
        "current": "hotline",
    }
    return render(request, "app/hotline.html", context)


def forgetpass(request):
    if request.user.is_authenticated:
        pass
    else:
        items = []
        order = {"get_cart_items": 0, "get_cart_total": 0}
        cartItems = order["get_cart_items"]
        user_info = None

    #       email = request.POST.get('email')
    #      try:
    #              user = User.objects.get(email=email)
    #              new_password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))
    #              user.set_password(new_password)
    #             user.save()
    #             send_mail(
    #                     'Password Reset',
    #                    f'Your new password: {new_password}',
    #                    'from@example.com',
    #                    [email],
    #                    fail_silently=False,
    #           )
    #           messages.success(request, 'Mật khẩu đã được thay đổi, check email để lấy mật khẩu')
    #               return redirect('login')
    #      except User.DoesNotExist:
    #             messages.info(request, 'Không có tài khoản nào với email này')
    #             return redirect('forget_pass')
    context = {
        "user_not_login": "show",
        "user_login": "hidden",
        "cartItems": cartItems,
    }
    return render(request, "app/forget-password.html", context)


def index(request):
    return render(request, "payment/index.html", {"title": "Danh sách demo"})


def hmacsha512(key, data):
    byteKey = key.encode("utf-8")
    byteData = data.encode("utf-8")
    return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()


def get_cart_total(request):
    if request.user.is_authenticated:
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        total = order.get_cart_total()
        return JsonResponse({"total": total})
    else:
        return JsonResponse({"error": "User is not authenticated"})


def payment(request):
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            customer = request.user
            # Lấy giỏ hàng hiện tại
            order, created = Order.objects.get_or_create(
                customer=customer, complete=False
            )

            # Dùng order.id làm order_id
            order_id = str(order.id)
            amount = form.cleaned_data["amount"]
            order_desc = form.cleaned_data["order_desc"]
            bank_code = form.cleaned_data["bank_code"]
            language = form.cleaned_data["language"]
            ipaddr = get_client_ip(request)

            # Build URL Payment
            vnp = vnpay()
            vnp.requestData["vnp_Version"] = "2.1.0"
            vnp.requestData["vnp_Command"] = "pay"
            vnp.requestData["vnp_TmnCode"] = settings.VNPAY_TMN_CODE
            vnp.requestData["vnp_Amount"] = amount * 100
            vnp.requestData["vnp_CurrCode"] = "VND"
            vnp.requestData["vnp_TxnRef"] = order_id
            vnp.requestData["vnp_OrderInfo"] = order_desc
            vnp.requestData["vnp_OrderType"] = form.cleaned_data["order_type"]

            # Ngôn ngữ
            vnp.requestData["vnp_Locale"] = language if language else "vn"

            # Ngân hàng
            if bank_code:
                vnp.requestData["vnp_BankCode"] = bank_code

            vnp.requestData["vnp_CreateDate"] = datetime.now().strftime("%Y%m%d%H%M%S")
            vnp.requestData["vnp_IpAddr"] = ipaddr
            vnp.requestData["vnp_ReturnUrl"] = settings.VNPAY_RETURN_URL

            vnpay_payment_url = vnp.get_payment_url(
                settings.VNPAY_PAYMENT_URL, settings.VNPAY_HASH_SECRET_KEY
            )
            return redirect(vnpay_payment_url)
    else:
        if request.user.is_authenticated:
            order, _ = Order.objects.get_or_create(
                customer=request.user, complete=False
            )
            order_id = order.id
        else:
            order_id = 0
        return render(
            request,
            "payment/payment.html",
            {"title": "Thanh toán", "order_id": order_id},
        )


def payment_ipn(request):
    inputData = request.GET
    if inputData:
        vnp = vnpay()
        vnp.responseData = inputData.dict()
        order_id = inputData["vnp_TxnRef"]
        amount = inputData["vnp_Amount"]
        order_desc = inputData["vnp_OrderInfo"]
        vnp_TransactionNo = inputData["vnp_TransactionNo"]
        vnp_ResponseCode = inputData["vnp_ResponseCode"]
        vnp_TmnCode = inputData["vnp_TmnCode"]
        vnp_PayDate = inputData["vnp_PayDate"]
        vnp_BankCode = inputData["vnp_BankCode"]
        vnp_CardType = inputData["vnp_CardType"]
        if vnp.validate_response(settings.VNPAY_HASH_SECRET_KEY):
            # Check & Update Order Status in your Database
            # Your code here
            firstTimeUpdate = True
            totalamount = True
            if totalamount:
                if firstTimeUpdate:
                    if vnp_ResponseCode == "00":
                        print("Payment Success. Your code implement here")
                    else:
                        print("Payment Error. Your code implement here")

                    # Return VNPAY: Merchant update success
                    result = JsonResponse(
                        {"RspCode": "00", "Message": "Confirm Success"}
                    )
                else:
                    # Already Update
                    result = JsonResponse(
                        {"RspCode": "02", "Message": "Order Already Update"}
                    )
            else:
                # invalid amount
                result = JsonResponse({"RspCode": "04", "Message": "invalid amount"})
        else:
            # Invalid Signature
            result = JsonResponse({"RspCode": "97", "Message": "Invalid Signature"})
    else:
        result = JsonResponse({"RspCode": "99", "Message": "Invalid request"})

    return result


def payment_return(request):
    inputData = request.GET
    if not inputData:
        return render(
            request,
            "payment/payment_return.html",
            {"title": "Kết quả thanh toán", "result": "Không có dữ liệu trả về"},
        )

    vnp = vnpay()
    vnp.responseData = inputData.dict()

    order_id = inputData.get("vnp_TxnRef")
    amount = int(inputData.get("vnp_Amount", 0)) / 100
    order_desc = inputData.get("vnp_OrderInfo", "")
    vnp_TransactionNo = inputData.get("vnp_TransactionNo", "")
    vnp_ResponseCode = inputData.get("vnp_ResponseCode", "")

    # 🔹 Lưu log giao dịch
    Payment_VNPay.objects.create(
        order_id=order_id,
        amount=amount,
        order_desc=order_desc,
        vnp_TransactionNo=vnp_TransactionNo,
        vnp_ResponseCode=vnp_ResponseCode,
    )

    # 🔹 Kiểm tra chữ ký
    if not vnp.validate_response(settings.VNPAY_HASH_SECRET_KEY):
        return render(
            request,
            "payment/payment_return.html",
            {
                "title": "Kết quả thanh toán",
                "result": "Lỗi",
                "order_id": order_id,
                "amount": amount,
                "order_desc": order_desc,
                "vnp_TransactionNo": vnp_TransactionNo,
                "vnp_ResponseCode": vnp_ResponseCode,
                "msg": "Sai checksum",
            },
        )

    # 🔹 Nếu giao dịch thành công
    if vnp_ResponseCode == "00":
        try:
            order = Order.objects.get(id=order_id, complete=False)
            order.complete = True
            order.date_order = timezone.now()
            order.save()

            # 🔥 Cập nhật số lượng sản phẩm
            for item in order.order_items.all():
                product = item.product
                if product:
                    product.stock = max(product.stock - item.quantity, 0)
                    product.sold += item.quantity
                    product.save()

            # ✅ Tạo giỏ hàng mới cho user
            Order.objects.get_or_create(customer=order.customer, complete=False)

        except Order.DoesNotExist:
            pass

        return render(
            request,
            "payment/payment_return.html",
            {
                "title": "Kết quả thanh toán",
                "result": "Thành công",
                "order_id": order_id,
                "amount": amount,
                "order_desc": order_desc,
                "vnp_TransactionNo": vnp_TransactionNo,
                "vnp_ResponseCode": vnp_ResponseCode,
            },
        )

    # 🔹 Nếu giao dịch thất bại
    return render(
        request,
        "payment/payment_return.html",
        {
            "title": "Kết quả thanh toán",
            "result": "Lỗi",
            "order_id": order_id,
            "amount": amount,
            "order_desc": order_desc,
            "vnp_TransactionNo": vnp_TransactionNo,
            "vnp_ResponseCode": vnp_ResponseCode,
        },
    )


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


n = random.randint(10**11, 10**12 - 1)
n_str = str(n)
while len(n_str) < 12:
    n_str = "0" + n_str


def query(request):
    if request.method == "GET":
        return render(
            request, "payment/query.html", {"title": "Kiểm tra kết quả giao dịch"}
        )

    url = settings.VNPAY_API_URL
    secret_key = settings.VNPAY_HASH_SECRET_KEY
    vnp_TmnCode = settings.VNPAY_TMN_CODE
    vnp_Version = "2.1.0"

    vnp_RequestId = n_str
    vnp_Command = "querydr"
    vnp_TxnRef = request.POST["order_id"]
    vnp_OrderInfo = "kiem tra gd"
    vnp_TransactionDate = request.POST["trans_date"]
    vnp_CreateDate = datetime.now().strftime("%Y%m%d%H%M%S")
    vnp_IpAddr = get_client_ip(request)

    hash_data = "|".join(
        [
            vnp_RequestId,
            vnp_Version,
            vnp_Command,
            vnp_TmnCode,
            vnp_TxnRef,
            vnp_TransactionDate,
            vnp_CreateDate,
            vnp_IpAddr,
            vnp_OrderInfo,
        ]
    )

    secure_hash = hmac.new(
        secret_key.encode(), hash_data.encode(), hashlib.sha512
    ).hexdigest()

    data = {
        "vnp_RequestId": vnp_RequestId,
        "vnp_TmnCode": vnp_TmnCode,
        "vnp_Command": vnp_Command,
        "vnp_TxnRef": vnp_TxnRef,
        "vnp_OrderInfo": vnp_OrderInfo,
        "vnp_TransactionDate": vnp_TransactionDate,
        "vnp_CreateDate": vnp_CreateDate,
        "vnp_IpAddr": vnp_IpAddr,
        "vnp_Version": vnp_Version,
        "vnp_SecureHash": secure_hash,
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        response_json = json.loads(response.text)
    else:
        response_json = {
            "error": f"Request failed with status code: {response.status_code}"
        }

    return render(
        request,
        "payment/query.html",
        {"title": "Kiểm tra kết quả giao dịch", "response_json": response_json},
    )


def refund(request):
    if request.method == "GET":
        return render(request, "payment/refund.html", {"title": "Hoàn tiền giao dịch"})

    url = settings.VNPAY_API_URL
    secret_key = settings.VNPAY_HASH_SECRET_KEY
    vnp_TmnCode = settings.VNPAY_TMN_CODE
    vnp_RequestId = n_str
    vnp_Version = "2.1.0"
    vnp_Command = "refund"
    vnp_TransactionType = request.POST["TransactionType"]
    vnp_TxnRef = request.POST["order_id"]
    vnp_Amount = request.POST["amount"]
    vnp_OrderInfo = request.POST["order_desc"]
    vnp_TransactionNo = "0"
    vnp_TransactionDate = request.POST["trans_date"]
    vnp_CreateDate = datetime.now().strftime("%Y%m%d%H%M%S")
    vnp_CreateBy = "user01"
    vnp_IpAddr = get_client_ip(request)

    hash_data = "|".join(
        [
            vnp_RequestId,
            vnp_Version,
            vnp_Command,
            vnp_TmnCode,
            vnp_TransactionType,
            vnp_TxnRef,
            vnp_Amount,
            vnp_TransactionNo,
            vnp_TransactionDate,
            vnp_CreateBy,
            vnp_CreateDate,
            vnp_IpAddr,
            vnp_OrderInfo,
        ]
    )

    secure_hash = hmac.new(
        secret_key.encode(), hash_data.encode(), hashlib.sha512
    ).hexdigest()

    data = {
        "vnp_RequestId": vnp_RequestId,
        "vnp_TmnCode": vnp_TmnCode,
        "vnp_Command": vnp_Command,
        "vnp_TxnRef": vnp_TxnRef,
        "vnp_Amount": vnp_Amount,
        "vnp_OrderInfo": vnp_OrderInfo,
        "vnp_TransactionDate": vnp_TransactionDate,
        "vnp_CreateDate": vnp_CreateDate,
        "vnp_IpAddr": vnp_IpAddr,
        "vnp_TransactionType": vnp_TransactionType,
        "vnp_TransactionNo": vnp_TransactionNo,
        "vnp_CreateBy": vnp_CreateBy,
        "vnp_Version": vnp_Version,
        "vnp_SecureHash": secure_hash,
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        response_json = json.loads(response.text)
    else:
        response_json = {
            "error": f"Request failed with status code: {response.status_code}"
        }

    return render(
        request,
        "payment/refund.html",
        {"title": "Kết quả hoàn tiền giao dịch", "response_json": response_json},
    )


# chỉ cho staff/superuser
def staff_required(user):
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(staff_required)
def manage_dashboard(request):
    categories = Category.objects.filter(is_sub=False)  # 🔹 luôn khai báo
    order, _ = Order.objects.get_or_create(customer=request.user, complete=False)
    cartItems = order.get_cart_items
    # Tổng doanh thu = sum(quantity * price)
    total_revenue = (
        OrderItem.objects.filter(order__complete=True).aggregate(
            total=Sum(F("quantity") * F("product__price"))
        )["total"]
        or 0
    )

    # Tổng đơn hàng hoàn tất
    total_orders = Order.objects.filter(complete=True).count()

    # Tổng khách hàng (chỉ tính user thường, loại staff/admin)
    total_customers = User.objects.filter(is_staff=False).count()

    # Doanh thu theo tháng trong năm hiện tại
    current_year = now().year
    months = []
    monthly_revenue = []
    for m in range(1, 13):
        revenue = (
            OrderItem.objects.filter(
                order__complete=True,
                date_added__year=current_year,
                date_added__month=m,
            ).aggregate(total=Sum(F("quantity") * F("product__price")))["total"]
            or 0
        )
        months.append(calendar.month_abbr[m])  # Jan, Feb, ...
        monthly_revenue.append(revenue)

    # Doanh thu theo khách hàng (top 10)
    customer_data = (
        OrderItem.objects.filter(order__complete=True)
        .values("order__customer__username")
        .annotate(total=Sum(F("quantity") * F("product__price")))
        .order_by("-total")[:10]
    )
    customer_names = [c["order__customer__username"] for c in customer_data]
    customer_revenue = [c["total"] for c in customer_data]

    # Top sản phẩm bán chạy
    top_products = (
        OrderItem.objects.filter(order__complete=True)
        .values(name=F("product__name"))
        .annotate(
            total_quantity=Sum("quantity"),
            total_revenue=Sum(F("quantity") * F("product__price")),
        )
        .order_by("-total_quantity")[:5]
    )
    product_names = [p["name"] for p in top_products]
    product_revenue = [p["total_revenue"] for p in top_products]

    context = {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_customers": total_customers,
        "months": months,
        "monthly_revenue": monthly_revenue,
        "customer_names": customer_names,
        "customer_revenue": customer_revenue,
        "top_products": top_products,
        "product_names": product_names,
        "product_revenue": product_revenue,
        "categories": categories,
        "cartItems": cartItems,
        "current": "manage",
    }
    return render(request, "app/manage_dashboard.html", context)


@login_required
@user_passes_test(staff_required)
def manage_products(request):
    products = Product.objects.all()
    categories = Category.objects.filter(is_sub=False)  # 🔹 luôn khai báo
    order, _ = Order.objects.get_or_create(customer=request.user, complete=False)
    cartItems = order.get_cart_items

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()  # Lưu sản phẩm trước

            # 👉 Xử lý lưu ảnh phụ
            extra_images = request.FILES.getlist("extra_images")
            for img in extra_images:
                ProductImage.objects.create(product=product, image=img)

            messages.success(
                request, f"🎉 Sản phẩm '{product.name}' đã được thêm thành công!"
            )
            return redirect("manage_products")
        else:
            messages.error(
                request, "❌ Có lỗi xảy ra khi thêm sản phẩm, vui lòng thử lại."
            )
    else:
        form = ProductForm()

    return render(
        request,
        "app/manage_products.html",
        {
            "form": form,
            "products": products,
            "categories": categories,
            "cartItems": cartItems,
            "current": "manage",
        },
    )


@login_required
@user_passes_test(staff_required)
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    categories = Category.objects.filter(is_sub=False)  # 🔹 luôn khai báo
    order, _ = Order.objects.get_or_create(customer=request.user, complete=False)
    cartItems = order.get_cart_items
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(
                request, f"✏️ Sản phẩm '{product.name}' đã được cập nhật thành công!"
            )
            return redirect("manage_products")
        else:
            messages.error(request, f"❌ Không thể cập nhật sản phẩm '{product.name}'.")
    else:
        form = ProductForm(instance=product)
    return render(
        request,
        "app/edit_product.html",
        {
            "form": form,
            "product": product,
            "categories": categories,
            "cartItems": cartItems,
            "current": "manage",
        },
    )


@login_required
@user_passes_test(staff_required)
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product_name = product.name
    product.delete()
    messages.success(request, f"🗑️ Sản phẩm '{product_name}' đã được xóa thành công!")
    return redirect("manage_products")


# Quản lý đơn hàng checkout
@csrf_exempt
def place_order(request):
    if request.user.is_authenticated and request.method == "POST":
        customer = request.user
        try:
            order = Order.objects.get(customer=customer, complete=False)
        except Order.DoesNotExist:
            return JsonResponse(
                {"error": "Không có đơn hàng nào để hoàn tất"}, status=400
            )

        # ✅ Hoàn tất đơn hàng
        order.complete = True
        order.date_order = timezone.now()
        order.save()

        # ✅ Luôn tạo giỏ hàng mới rỗng cho user
        Order.objects.get_or_create(customer=customer, complete=False)

        return JsonResponse({"success": True})

    return JsonResponse({"error": "Yêu cầu không hợp lệ"}, status=400)


# Hàm ước tính thời gian vận chuyển dựa trên địa chỉ
def estimate_shipping(user_address, shop_address="Hồ Chí Minh"):
    if not user_address:
        return "Không rõ địa chỉ"

    # Giả lập khoảng cách đơn giản theo tỉnh/thành
    if "Hồ Chí Minh" in user_address or "Sài Gòn" in user_address:
        return "2 - 3 ngày (nội thành)"
    elif "Hà Nội" in user_address:
        return "3 - 5 ngày"
    elif "Đà Nẵng" in user_address:
        return "3 - 4 ngày"
    else:
        return "4 - 7 ngày (toàn quốc)"


# Form tố cáo sản phẩm
@login_required
def report_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        reason = request.POST.get("reason")
        ProductReport.objects.create(product=product, user=request.user, reason=reason)
        messages.success(request, "🚨 Đã gửi tố cáo sản phẩm.")
        return redirect("detail")  # hoặc redirect("detail") kèm id nếu cần

    return render(request, "app/report_form.html", {"product": product})


# ✅ Quản lý đơn hàng cho admin/staff
@login_required
@user_passes_test(staff_required)
def manage_orders(request):
    # Chỉ lấy đơn hàng có sản phẩm hợp lệ (total > 0)
    orders = (
        Order.objects.annotate(
            total=Sum(F("order_items__quantity") * F("order_items__product__price"))
        )
        .filter(total__gt=0)
        .order_by("-date_order")
    )

    # Nếu đơn mới nào đó chưa có status thì ép confirmed luôn
    for order in orders:
        if not order.status:
            order.status = "confirmed"
            order.save(update_fields=["status"])

    return render(
        request,
        "app/manage_orders.html",
        {"orders": orders, "current": "manage"},
    )


# ✅ Cập nhật trạng thái đơn hàng (phiên bản chuyên nghiệp, đã sửa cú pháp)
@login_required
@user_passes_test(staff_required)
def update_order_status(request, order_id, status):
    order = get_object_or_404(Order, id=order_id)

    # Nếu trạng thái trống thì ép thành confirmed
    if not order.status:
        order.status = "confirmed"

    order.status = status
    if status == "delivered":
        order.complete = True
    order.save()

    # ==== GỬI EMAIL THÔNG BÁO ====
    if order.customer and order.customer.email:
        subject = f"[TheGioiSua] Cập nhật trạng thái đơn hàng #{order.id}"

        order_url = request.build_absolute_uri(reverse("order_detail", args=[order.id]))

        # Nếu get_cart_total là @property thì dùng như dưới, nếu là method thì đổi thành order.get_cart_total()
        order_total_str = f"{order.get_cart_total:,.0f} ₫"

        message = (
            f"Xin chào {order.customer.get_full_name() or order.customer.username},\n\n"
            f"Cảm ơn bạn đã mua hàng tại TheGioiSua!\n\n"
            f"Đơn hàng của bạn (Mã đơn: #{order.id}) hiện đã được cập nhật trạng thái:\n"
            f"➡  {order.get_status_display().upper()}\n\n"
            f"Thông tin chi tiết đơn hàng:\n"
            f"- Ngày đặt: {order.date_order.strftime('%d/%m/%Y %H:%M')}\n"
            f"- Tổng giá trị: {order_total_str}\n\n"
            f"Bạn có thể xem chi tiết đơn hàng tại đường dẫn sau:\n"
            f"{order_url}\n\n"
            f"--------------------------------------\n"
            f"TheGioiSua - Nâng niu sức khỏe từng giọt sữa\n"
            f"Website: https://thegioisua.pythonanywhere.com\n"
            f"Hỗ trợ khách hàng: support@thegioisua.vn\n"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[order.customer.email],
            fail_silently=True,
        )

    messages.success(
        request,
        f"Đơn hàng #{order.id} đã được cập nhật trạng thái '{order.get_status_display()}'.",
    )
    return redirect("manage_orders")


# Thêm trang xem đơn hàng cho khách hàng
@login_required
def my_orders(request):
    orders = Order.objects.filter(customer=request.user, complete=True).order_by(
        "-date_order"
    )
    return render(
        request, "app/my_orders.html", {"orders": orders, "current": "my_orders"}
    )


# ✅ Khách hàng xác nhận đã nhận hàng
@login_required
def confirm_received(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Chỉ chủ đơn hàng mới được confirm
    if request.user != order.customer:
        return redirect("my_orders")

    order.status = "completed"  # cập nhật trạng thái
    order.complete = True
    order.save()

    messages.success(request, f"Bạn đã xác nhận đơn hàng #{order.id} hoàn tất.")

    return redirect("order_detail", order_id=order.id)


# ✅ Xem chi tiết đơn hàng
@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.order_items.select_related("product").all()

    # ✅ Nếu không phải staff/admin → chỉ cho xem đơn của chính họ
    if not request.user.is_staff and order.customer != request.user:
        return redirect("my_orders")

    context = {
        "order": order,
        "items": items,
    }
    return render(request, "app/order_detail.html", context)


# ️ Đánh giá sản phẩm sau khi nhận hàng
@login_required
def review_product(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Chỉ chủ đơn hàng mới được đánh giá
    if request.user != order.customer:
        return redirect("my_orders")

    items = order.order_items.all()

    if request.method == "POST":
        success = False
        for item in items:
            form = ReviewForm(request.POST, prefix=str(item.id))
            if form.is_valid():
                Review.objects.create(
                    order=order,
                    product=item.product,
                    customer=request.user,
                    rating=form.cleaned_data["rating"],
                    comment=form.cleaned_data["comment"],
                )
                success = True
        if success:
            messages.success(
                request, f"Bạn đã đánh giá đơn hàng #{order.id} thành công."
            )
        else:
            messages.warning(request, "Bạn chưa nhập đánh giá hợp lệ nào.")
        return redirect("order_detail", order_id=order.id)
    else:
        # ✅ Truyền (item, form) thay vì dict
        forms = [(item, ReviewForm(prefix=str(item.id))) for item in items]

    return render(
        request,
        "app/review_product.html",
        {"order": order, "forms": forms},
    )


# Xử lý hoàn tất đơn hàng (checkout)
@login_required
def process_order(request):
    customer = request.user
    order = Order.objects.filter(customer=customer, complete=False).first()

    if not order or order.get_cart_total == 0:
        # Nếu có order rác thì xoá luôn
        if order:
            order.delete()
        messages.error(request, "Không có đơn hàng nào để hoàn tất.")
        return redirect("cart")

    order.transaction_id = timezone.now().timestamp()
    payment_method = request.POST.get("payment_method", "cod")

    if payment_method == "cod":
        order.status = "pending"
        order.complete = True
        order.save()
        messages.success(request, f"Đặt hàng thành công! Mã đơn: #{order.id}")
        return redirect("my_orders")

    elif payment_method == "vnpay":
        return redirect("payment_vnpay", order_id=order.id)

    return redirect("cart")


# Quản lý người dùng (chỉ admin/staff)
@login_required
@user_passes_test(staff_required)
def manage_user(request):
    users = User.objects.filter(is_staff=False)  # chỉ lấy khách hàng
    return render(
        request, "app/manage_user.html", {"users": users, "current": "manage_user"}
    )


@login_required
@user_passes_test(staff_required)
def toggle_user_status(request, user_id):
    user = get_object_or_404(
        User, id=user_id, is_staff=False
    )  # chỉ áp dụng cho khách hàng
    user.is_active = not user.is_active
    user.save()
    if user.is_active:
        messages.success(request, f"Tài khoản {user.username} đã được mở khóa.")
    else:
        messages.warning(request, f"Tài khoản {user.username} đã bị khóa.")
    return redirect("manage_user")


# Hủy đơn hàng (nếu chưa hoàn tất)
@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)

    # Chỉ được hủy nếu chưa "completed" hoặc "cancelled"
    if order.status not in ["completed", "cancelled"] and request.method == "POST":
        reason = request.POST.get("reason", "")
        order.status = "cancelled"
        order.complete = False

        # Nếu có field cancel_reason thì lưu thêm lý do
        if hasattr(order, "cancel_reason"):
            order.cancel_reason = reason

        order.save(
            update_fields=["status", "complete"]
            + (["cancel_reason"] if hasattr(order, "cancel_reason") else [])
        )
        messages.success(request, "Bạn đã hủy đơn hàng thành công.")
    else:
        messages.error(request, "Không thể hủy đơn này.")

    return redirect("order_detail", order_id=order.id)


@csrf_exempt
def send_otp(request):
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email")

        if not email:
            return JsonResponse({"success": False, "error": "Thiếu email"})

        otp = str(random.randint(100000, 999999))
        request.session["otp_code"] = otp

        try:
            send_mail(
                subject="Mã OTP xác nhận đơn hàng",
                message=f"Mã OTP của bạn là: {otp}",
                from_email="yourgmail@gmail.com",
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

        return JsonResponse({"success": True, "msg": "OTP đã được gửi"})
    return JsonResponse({"success": False, "error": "Yêu cầu không hợp lệ"})


# Update 4


# Thêm địa chỉ mới qua AJAX
@login_required
@csrf_exempt
def add_address_ajax(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")
        address_line = request.POST.get("address_line")
        is_default = request.POST.get("is_default") == "true"

        if not (full_name and phone and address_line):
            return JsonResponse({"success": False, "error": "Thiếu dữ liệu"})

        addr = Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone=phone,
            address_line=address_line,
            is_default=is_default,
        )

        # Nếu chọn mặc định thì bỏ mặc định ở các địa chỉ khác
        if is_default:
            Address.objects.filter(user=request.user).exclude(id=addr.id).update(
                is_default=False
            )

        return JsonResponse(
            {
                "success": True,
                "id": addr.id,
                "text": f"{addr.full_name} - {addr.address_line} ({addr.phone})",
            }
        )
    return JsonResponse({"success": False, "error": "Phương thức không hợp lệ"})


# =========================
# Cập nhật địa chỉ
# =========================
@login_required
@csrf_exempt
def update_address_ajax(request):
    if request.method == "POST":
        addr_id = request.POST.get("id")
        if not addr_id:
            return JsonResponse({"success": False, "error": "Thiếu ID"})

        try:
            addr = Address.objects.get(id=addr_id, user=request.user)
            addr.full_name = request.POST.get("full_name")
            addr.phone = request.POST.get("phone")
            addr.address_line = request.POST.get("address_line")
            addr.is_default = request.POST.get("is_default") == "true"
            addr.save()

            # Nếu chọn mặc định thì bỏ mặc định ở các địa chỉ khác
            if addr.is_default:
                Address.objects.filter(user=request.user).exclude(id=addr.id).update(
                    is_default=False
                )

            return JsonResponse({"success": True})
        except Address.DoesNotExist:
            return JsonResponse({"success": False, "error": "Không tìm thấy địa chỉ"})

    return JsonResponse({"success": False, "error": "Phương thức không hợp lệ"})


@login_required
def delete_address_ajax(request):
    if request.method == "POST":
        id = request.POST.get("id")
        try:
            Address.objects.get(id=id, user=request.user).delete()
            return JsonResponse({"success": True})
        except Address.DoesNotExist:
            return JsonResponse({"success": False, "error": "Address not found"})
    return JsonResponse({"success": False, "error": "Invalid request"})


@login_required
def get_address_ajax(request, id):
    try:
        addr = Address.objects.get(id=id, user=request.user)
        # Giả sử address_line lưu theo format: "số nhà, phường/xã, quận/huyện, tỉnh/thành"
        parts = [p.strip() for p in addr.address_line.split(",")]

        detail = parts[0] if len(parts) > 0 else ""
        ward = parts[1] if len(parts) > 1 else ""
        district = parts[2] if len(parts) > 2 else ""
        province = parts[3] if len(parts) > 3 else ""

        return JsonResponse(
            {
                "success": True,
                "id": addr.id,
                "full_name": addr.full_name,
                "phone": addr.phone,
                "detail": detail,
                "ward": ward,
                "district": district,
                "province": province,
                "is_default": addr.is_default,
            }
        )
    except Address.DoesNotExist:
        return JsonResponse({"success": False, "error": "Address not found"})
