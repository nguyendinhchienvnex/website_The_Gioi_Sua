from django.contrib import admin
from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("register/", views.register, name="register"),
    path("change_account", views.change_account, name="change_account"),
    path("register_api/", views.register_api, name="register_api"),
    path("forget_pass/", views.forgetpass, name="forget_pass"),
    path("login/", views.login_account, name="login"),
    path("profile/", views.profile, name="profile"),
    path("search/", views.search, name="search"),
    path("logout/", views.logout_account, name="logout"),
    path("", views.home, name="home"),
    path("product_api/", views.product_api, name="product_api"),
    path("cart/", views.cart, name="cart"),
    path("cart_api/<int:user_id>/", views.cart_api, name="cart-api"),
    path("checkout/", views.checkout, name="checkout"),
    path("update_item/", views.updateItem, name="update_item"),
    path("category/", views.category, name="category"),
    path("category_api/", views.category_api, name="category_api"),
    path("detail/", views.detail, name="detail"),
    path("hotline/", views.hotline, name="hotline"),
    path("userId_api/", views.userId_api, name="userId_api"),
    path("pay", views.index, name="index"),
    path("payment", views.payment, name="payment"),
    path("payment_ipn", views.payment_ipn, name="payment_ipn"),
    path("payment_return", views.payment_return, name="payment_return"),
    path("query", views.query, name="query"),
    path("refund", views.refund, name="refund"),
    path("total", views.get_cart_total, name="total"),
    # path('manage_dashboard', views.manage_dashboard, name='manage_dashboard'),
    path("manage/dashboard/", views.manage_dashboard, name="manage_dashboard"),
    path("manage/products/", views.manage_products, name="manage_products"),
    path("manage_user/", views.manage_user, name="manage_user"),
    path("manage/products/<int:pk>/edit/", views.edit_product, name="edit_product"),
    path(
        "manage/products/<int:pk>/delete/", views.delete_product, name="delete_product"
    ),
    path("place_order/", views.place_order, name="place_order"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    # Update3
    path("product/<int:pk>/report/", views.report_product, name="report_product"),
    path("manage/orders/", views.manage_orders, name="manage_orders"),
    path(
        "manage/orders/<int:order_id>/<str:status>/",
        views.update_order_status,
        name="update_order_status",
    ),
    path("manage/my_order/", views.my_orders, name="my_orders"),
    path("manage/order/<int:order_id>/", views.order_detail, name="order_detail"),
    path(
        "orders/<int:order_id>/confirm/",
        views.confirm_received,
        name="confirm_received",
    ),
    path("orders/<int:order_id>/review/", views.review_product, name="review_product"),
    path(
        "toggle_user_status/<int:user_id>/",
        views.toggle_user_status,
        name="toggle_user_status",
    ),
    path("my_order/<int:order_id>/", views.order_detail, name="order_detail"),
    path("order/<int:order_id>/cancel/", views.cancel_order, name="cancel_order"),
    path("send_otp/", views.send_otp, name="send_otp"),
]
