import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings as django_settings
from huggingface_hub import InferenceClient

import os

from .models import ChatSession, ChatMessage

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

SYSTEM_PROMPT_TEMPLATE = """Ты — AI-ассистент интернет-магазина ServerPro, специализирующегося на серверном и сетевом оборудовании.
Ты помогаешь клиентам с вопросами о товарах, услугах, заказах и техподдержке.

Контакты магазина:
- Телефон: {phone}
- Email: {email}
- Адрес: {address}

{catalog_info}

{services_info}

Правила:
- Отвечай кратко и по делу, на русском языке
- Используй данные о товарах и услугах выше для ответов
- Если клиент спрашивает о конкретном товаре, которого нет в списке, предложи связаться с менеджером
- Будь дружелюбным и профессиональным
- Указывай реальные цены из каталога, не выдумывай
- Для оформления заказа направляй на сайт или предложи позвонить"""

# Free models on HuggingFace Inference API (tried in order)
HF_MODELS = [
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
]


def get_client():
    token = os.getenv("HF_API_TOKEN")
    return InferenceClient(token=token)


def get_site_context():
    """Build system prompt with real data from DB."""
    from apps.dashboard.models import DashboardSettings
    from apps.products.models import Product, Category
    from apps.services.models import Service

    settings = DashboardSettings.get_settings()

    # Get categories with product counts
    categories = Category.objects.filter(is_active=True, parent=None)
    cat_lines = []
    for cat in categories:
        children = cat.children.filter(is_active=True)
        child_names = ', '.join(c.name for c in children)
        if child_names:
            cat_lines.append(f"- {cat.name} ({child_names})")
        else:
            cat_lines.append(f"- {cat.name}")

    # Get popular/featured products (limit to avoid huge prompt)
    products = Product.objects.filter(is_active=True).select_related('category', 'brand')[:30]
    product_lines = []
    for p in products:
        price_str = f"{p.price:,.0f} руб.".replace(',', ' ')
        if p.old_price and p.old_price > p.price:
            old = f"{p.old_price:,.0f}".replace(',', ' ')
            price_str += f" (скидка, было {old} руб.)"
        stock = "в наличии" if p.stock > 0 else "под заказ"
        product_lines.append(f"- {p.name} ({p.category.name}) — {price_str}, {stock}")

    catalog_info = "Категории товаров:\n" + '\n'.join(cat_lines)
    if product_lines:
        catalog_info += "\n\nТовары в каталоге:\n" + '\n'.join(product_lines)

    # Services
    services = Service.objects.filter(is_active=True)
    service_lines = []
    for s in services:
        price_str = f"от {s.price:,.0f} руб.".replace(',', ' ')
        service_lines.append(f"- {s.name} — {price_str}")

    services_info = ""
    if service_lines:
        services_info = "Услуги:\n" + '\n'.join(service_lines)

    return SYSTEM_PROMPT_TEMPLATE.format(
        phone=settings.phone or '+7 (495) 123-45-67',
        email=settings.email or 'info@serverpro.ru',
        address=settings.address or '',
        catalog_info=catalog_info,
        services_info=services_info,
    )


def get_or_create_session(request):
    if request.user.is_authenticated:
        session, _ = ChatSession.objects.get_or_create(
            user=request.user,
            defaults={'session_key': request.session.session_key or ''}
        )
    else:
        if not request.session.session_key:
            request.session.create()
        sk = request.session.session_key
        session, _ = ChatSession.objects.get_or_create(
            session_key=sk, user__isnull=True
        )
    return session


def build_messages(session, user_message):
    system_prompt = get_site_context()
    messages = [{"role": "system", "content": system_prompt}]
    history = session.messages.order_by('-created_at')[:10]
    for msg in reversed(list(history)):
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})
    return messages


@require_POST
def chat_send(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_message = data.get('message', '').strip()
    if not user_message:
        return JsonResponse({'error': 'Empty message'}, status=400)
    if len(user_message) > 2000:
        return JsonResponse({'error': 'Message too long'}, status=400)

    session = get_or_create_session(request)
    ChatMessage.objects.create(session=session, role='user', content=user_message)

    messages = build_messages(session, user_message)

    reply = None
    client = get_client()
    for model_id in HF_MODELS:
        try:
            response = client.chat_completion(
                model=model_id,
                messages=messages,
                max_tokens=512,
                temperature=0.7,
            )
            reply = response.choices[0].message.content
            break
        except Exception as e:
            logger.warning(f"Model {model_id} failed: {e}")
            continue

    if not reply:
        reply = ("Извините, сервис временно недоступен. "
                 "Пожалуйста, свяжитесь с нами по телефону или через мессенджеры.")

    ChatMessage.objects.create(session=session, role='assistant', content=reply)

    return JsonResponse({'reply': reply})


@require_POST
def chat_clear(request):
    session = get_or_create_session(request)
    session.messages.all().delete()
    return JsonResponse({'status': 'ok'})


def chat_history(request):
    session = get_or_create_session(request)
    messages = session.messages.order_by('created_at')[:50]
    return JsonResponse({
        'messages': [
            {'role': m.role, 'content': m.content}
            for m in messages
        ]
    })
