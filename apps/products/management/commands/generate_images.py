"""
python manage.py generate_images  — generate placeholder images for all DB objects
"""
import os
from io import BytesIO
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings as django_settings

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

GRADIENTS = [
    ((41, 128, 185), (109, 213, 250)),
    ((142, 68, 173), (218, 112, 214)),
    ((39, 174, 96), (130, 224, 170)),
    ((231, 76, 60), (241, 148, 138)),
    ((243, 156, 18), (248, 196, 113)),
    ((44, 62, 80), (127, 140, 141)),
    ((22, 160, 133), (162, 217, 206)),
    ((192, 57, 43), (236, 112, 99)),
    ((52, 73, 94), (133, 146, 158)),
    ((46, 204, 113), (171, 235, 198)),
]

BRAND_COLORS = [
    (37, 99, 235), (220, 38, 38), (5, 150, 105), (124, 58, 237),
    (234, 88, 12), (14, 165, 233), (168, 85, 247), (236, 72, 153),
    (20, 184, 166), (245, 158, 11), (99, 102, 241), (34, 197, 94),
    (239, 68, 68), (59, 130, 246),
]


def file_exists(field):
    """Check if an ImageField has a valid file on disk."""
    if not field:
        return False
    try:
        return os.path.exists(field.path)
    except Exception:
        return False


def make_gradient(width, height, c1, c2):
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        r = int(c1[0] + (c2[0] - c1[0]) * y / height)
        g = int(c1[1] + (c2[1] - c1[1]) * y / height)
        b = int(c1[2] + (c2[2] - c1[2]) * y / height)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return img


def make_image(width=800, height=600, text='', index=0):
    colors = GRADIENTS[index % len(GRADIENTS)]
    img = make_gradient(width, height, colors[0], colors[1])
    if text:
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 28)
        except (IOError, OSError):
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (width - tw) // 2
        y = (height - th) // 2
        draw.text((x + 2, y + 2), text, fill=(0, 0, 0, 128), font=font)
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return buf.getvalue()


def make_brand_logo(name, index=0):
    """Create a wide, readable brand logo."""
    w, h = 320, 90
    bg = BRAND_COLORS[index % len(BRAND_COLORS)]
    img = Image.new('RGB', (w, h), bg)
    draw = ImageDraw.Draw(img)

    # Rounded corners via mask
    mask = Image.new('L', (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, w, h], radius=12, fill=255)

    try:
        font = ImageFont.truetype('arialbd.ttf', 30)
    except (IOError, OSError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), name, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = (w - tw) // 2, (h - th) // 2 - 2
    draw.text((x + 1, y + 1), name, fill=(0, 0, 0, 80), font=font)
    draw.text((x, y), name, fill=(255, 255, 255), font=font)

    result = Image.new('RGB', (w, h), (255, 255, 255))
    result.paste(img, mask=mask)

    buf = BytesIO()
    result.save(buf, format='PNG')
    return buf.getvalue()


def make_logo():
    """Create ServerPro logo."""
    logo_w, logo_h = 300, 80
    img = Image.new('RGBA', (logo_w, logo_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    icon_size = 56
    ix, iy = 8, 12
    draw.rounded_rectangle(
        [ix, iy, ix + icon_size, iy + icon_size],
        radius=14, fill=(37, 99, 235)
    )
    try:
        f1 = ImageFont.truetype('arialbd.ttf', 34)
    except (IOError, OSError):
        f1 = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), 'S', font=f1)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (ix + (icon_size - tw) // 2, iy + (icon_size - th) // 2 - 2),
        'S', fill=(255, 255, 255), font=f1
    )

    try:
        f2 = ImageFont.truetype('arialbd.ttf', 30)
    except (IOError, OSError):
        f2 = ImageFont.load_default()
    draw.text((ix + icon_size + 14, 20), 'Магазин серверов', fill=(30, 41, 59), font=f2)

    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def make_favicon():
    """Create ServerPro favicon."""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([4, 4, 60, 60], radius=14, fill=(37, 99, 235))
    try:
        font = ImageFont.truetype('arialbd.ttf', 36)
    except (IOError, OSError):
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), 'S', font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((size - tw) // 2, (size - th) // 2 - 2),
        'S', fill=(255, 255, 255), font=font
    )
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


class Command(BaseCommand):
    help = 'Generate placeholder images for DB objects'

    def handle(self, *args, **options):
        if not HAS_PILLOW:
            self.stderr.write('Pillow is required: pip install Pillow')
            return

        from apps.products.models import Product, Category, Brand
        from apps.services.models import Service, ServiceCategory
        from apps.blog.models import Post
        from apps.promotions.models import Promotion, Banner
        from apps.dashboard.models import DashboardSettings

        count = 0

        # Products
        for i, p in enumerate(Product.objects.all()):
            if not file_exists(p.main_image):
                data = make_image(800, 800, p.name[:30], i)
                p.main_image.save(f'product_{p.pk}.jpg', ContentFile(data), save=True)
                count += 1

        # Categories
        for i, c in enumerate(Category.objects.all()):
            if not file_exists(c.image):
                data = make_image(600, 400, c.name[:30], i + 3)
                c.image.save(f'cat_{c.pk}.jpg', ContentFile(data), save=True)
                count += 1

        # Brands — wide readable logos
        for i, b in enumerate(Brand.objects.all()):
            if not file_exists(b.logo):
                data = make_brand_logo(b.name, i)
                b.logo.save(f'brand_{b.pk}.png', ContentFile(data), save=True)
                count += 1

        # Services
        for i, s in enumerate(Service.objects.all()):
            if not file_exists(s.image):
                data = make_image(800, 600, s.name[:30], i + 2)
                s.image.save(f'service_{s.pk}.jpg', ContentFile(data), save=True)
                count += 1

        # Service Categories
        for i, sc in enumerate(ServiceCategory.objects.all()):
            if not file_exists(sc.image):
                data = make_image(600, 400, sc.name[:30], i + 4)
                sc.image.save(f'svc_cat_{sc.pk}.jpg', ContentFile(data), save=True)
                count += 1

        # Blog Posts
        for i, post in enumerate(Post.objects.all()):
            if not file_exists(post.image):
                data = make_image(1200, 630, post.title[:35], i + 1)
                post.image.save(f'post_{post.pk}.jpg', ContentFile(data), save=True)
                count += 1

        # Promotions
        for i, promo in enumerate(Promotion.objects.all()):
            if not file_exists(promo.image):
                data = make_image(800, 400, 'PROMO', i + 6)
                promo.image.save(f'promo_{promo.pk}.jpg', ContentFile(data), save=True)
                count += 1

        # Banners
        for i, banner in enumerate(Banner.objects.all()):
            if not file_exists(banner.image):
                data = make_image(1920, 600, 'Banner', i + 7)
                banner.image.save(f'banner_{banner.pk}.jpg', ContentFile(data), save=True)
                count += 1
            if not file_exists(banner.image_mobile):
                data = make_image(768, 400, 'Banner Mobile', i + 8)
                banner.image_mobile.save(f'banner_m_{banner.pk}.jpg', ContentFile(data), save=True)
                count += 1

        # Settings — logo & favicon
        try:
            ds = DashboardSettings.objects.get(pk=1)
            if not file_exists(ds.logo):
                data = make_logo()
                ds.logo.save('logo.png', ContentFile(data), save=True)
                count += 1
            if not file_exists(ds.favicon):
                data = make_favicon()
                ds.favicon.save('favicon.png', ContentFile(data), save=True)
                count += 1
        except DashboardSettings.DoesNotExist:
            pass

        self.stdout.write(self.style.SUCCESS(f'Generated {count} images'))
