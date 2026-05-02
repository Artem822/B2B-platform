"""
python manage.py seed_data          — создать все тестовые данные
python manage.py seed_data --clear  — очистить БД и создать заново
"""
import random
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed database with test data'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear DB first')

    def handle(self, *args, **options):
        from apps.products.models import Product, Category, Brand, Wishlist, ProductSpecification
        from apps.orders.models import Order, OrderItem, OrderStatusHistory
        from apps.services.models import (
            Service, ServiceCategory, Technician, ServiceRequest, ServiceRequestHistory
        )
        from apps.blog.models import Post, BlogCategory, Tag, Comment
        from apps.promotions.models import Promotion, PromoCode, Banner
        from apps.reviews.models import Review, ServiceReview
        from apps.accounts.models import Address, Notification
        from apps.dashboard.models import DashboardSettings

        if options['clear']:
            self.stdout.write('Clearing database...')
            Review.objects.all().delete()
            ServiceReview.objects.all().delete()
            OrderItem.objects.all().delete()
            OrderStatusHistory.objects.all().delete()
            Order.objects.all().delete()
            ServiceRequestHistory.objects.all().delete()
            ServiceRequest.objects.all().delete()
            Comment.objects.all().delete()
            Post.objects.all().delete()
            Tag.objects.all().delete()
            BlogCategory.objects.all().delete()
            Wishlist.objects.all().delete()
            ProductSpecification.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Brand.objects.all().delete()
            PromoCode.objects.all().delete()
            Promotion.objects.all().delete()
            Banner.objects.all().delete()
            Service.objects.all().delete()
            ServiceCategory.objects.all().delete()
            Technician.objects.all().delete()
            Notification.objects.all().delete()
            Address.objects.all().delete()
            User.objects.filter(role='client').delete()
            User.objects.filter(role='technician').delete()
            self.stdout.write(self.style.WARNING('DB cleared'))

        now = timezone.now()

        # ============================================================
        # 1. USERS
        # ============================================================
        self.stdout.write('Creating users...')

        admin, _ = User.objects.get_or_create(
            email='admin@serverpro.ru',
            defaults={
                'first_name': 'Админ', 'last_name': 'Системный',
                'role': 'admin', 'is_staff': True, 'is_superuser': True,
            }
        )
        admin.set_password('admin123')
        admin.save()

        manager, _ = User.objects.get_or_create(
            email='manager@serverpro.ru',
            defaults={
                'first_name': 'Ольга', 'last_name': 'Петрова',
                'role': 'manager', 'is_staff': True,
                'phone': '+7 (495) 200-10-01',
            }
        )
        manager.set_password('manager123')
        manager.save()

        tech_users_data = [
            ('tech1@serverpro.ru', 'Алексей', 'Козлов'),
            ('tech2@serverpro.ru', 'Дмитрий', 'Сидоров'),
            ('tech3@serverpro.ru', 'Игорь', 'Новиков'),
        ]
        tech_users = []
        for email, fn, ln in tech_users_data:
            u, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': fn, 'last_name': ln,
                    'role': 'technician', 'phone': '+7 (495) 200-20-0' + email[4],
                }
            )
            u.set_password('tech123')
            u.save()
            tech_users.append(u)

        client_data = [
            ('ivanov@example.com', 'Иван', 'Иванов', 'ООО "АльфаТех"', '7701234567'),
            ('petrova@example.com', 'Анна', 'Петрова', 'ИП Петрова А.С.', '7709876543'),
            ('sidorov@example.com', 'Сергей', 'Николаев', 'ООО "СерверСтрой"', '7705551234'),
            ('kuznetsov@example.com', 'Михаил', 'Кузнецов', 'ЗАО "ДатаЦентр"', '7703334455'),
            ('sokolova@example.com', 'Елена', 'Соколова', 'ООО "Инфраструктура+"', '7707778899'),
            ('morozov@example.com', 'Андрей', 'Морозов', 'ИП Морозов А.В.', '7702223344'),
            ('volkova@example.com', 'Наталья', 'Волкова', 'ООО "КлаудСервис"', '7706665577'),
            ('lebedev@example.com', 'Павел', 'Лебедев', 'АО "ТелекомПро"', '7704449988'),
        ]
        clients = []
        for email, fn, ln, company, inn in client_data:
            u, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': fn, 'last_name': ln, 'role': 'client',
                    'company_name': company, 'inn': inn,
                    'phone': f'+7 (9{random.randint(10,99)}) {random.randint(100,999)}-{random.randint(10,99)}-{random.randint(10,99)}',
                }
            )
            u.set_password('client123')
            u.save()
            clients.append(u)

        # Addresses
        cities = ['Москва', 'Санкт-Петербург', 'Казань', 'Новосибирск', 'Екатеринбург',
                  'Краснодар', 'Нижний Новгород', 'Самара']
        streets = ['ул. Ленина', 'пр. Мира', 'ул. Гагарина', 'ул. Пушкина',
                   'пр. Победы', 'ул. Советская', 'ул. Кирова', 'ул. Промышленная']
        for i, client in enumerate(clients):
            if not Address.objects.filter(user=client).exists():
                Address.objects.create(
                    user=client, title='Офис',
                    city=cities[i % len(cities)],
                    street=streets[i % len(streets)],
                    building=str(random.randint(1, 150)),
                    office=str(random.randint(1, 500)),
                    postal_code=f'{random.randint(100, 199)}0{random.randint(10,99)}',
                    is_default=True,
                )

        # ============================================================
        # 2. CATEGORIES (parent + children)
        # ============================================================
        self.stdout.write('Creating categories...')

        cat_tree = {
            'Серверы': ['Стоечные серверы', 'Башенные серверы', 'Блейд-серверы'],
            'Серверные компоненты': ['Процессоры', 'Оперативная память', 'Жёсткие диски и SSD', 'RAID-контроллеры', 'Блоки питания'],
            'Сетевое оборудование': ['Коммутаторы', 'Маршрутизаторы', 'Точки доступа Wi-Fi'],
            'Системы хранения': ['NAS-хранилища', 'SAN-массивы', 'Ленточные библиотеки'],
            'Серверные шкафы и стойки': ['Напольные шкафы', 'Настенные шкафы'],
            'ИБП и электропитание': ['Онлайн ИБП', 'Линейно-интерактивные ИБП', 'Стабилизаторы напряжения'],
        }
        all_categories = {}
        order_idx = 0
        for parent_name, children in cat_tree.items():
            parent, _ = Category.objects.get_or_create(
                name=parent_name,
                defaults={'is_active': True, 'order': order_idx, 'parent': None,
                          'description': f'Категория {parent_name.lower()} для серверного оборудования.'}
            )
            all_categories[parent_name] = parent
            order_idx += 1
            for child_name in children:
                child, _ = Category.objects.get_or_create(
                    name=child_name,
                    defaults={'parent': parent, 'is_active': True, 'order': order_idx,
                              'description': f'{child_name} — подкатегория раздела "{parent_name}".'}
                )
                all_categories[child_name] = child
                order_idx += 1

        # ============================================================
        # 3. BRANDS
        # ============================================================
        self.stdout.write('Creating brands...')

        brand_data = [
            ('Dell', 'https://dell.com'), ('HP Enterprise', 'https://hpe.com'),
            ('Lenovo', 'https://lenovo.com'), ('Supermicro', 'https://supermicro.com'),
            ('Intel', 'https://intel.com'), ('AMD', 'https://amd.com'),
            ('Samsung', 'https://samsung.com'), ('Seagate', 'https://seagate.com'),
            ('Cisco', 'https://cisco.com'), ('MikroTik', 'https://mikrotik.com'),
            ('APC', 'https://apc.com'), ('Synology', 'https://synology.com'),
            ('Western Digital', 'https://westerndigital.com'),
            ('Kingston', 'https://kingston.com'),
        ]
        all_brands = {}
        for name, website in brand_data:
            b, _ = Brand.objects.get_or_create(
                name=name, defaults={'website': website, 'is_active': True}
            )
            all_brands[name] = b

        # ============================================================
        # 4. PRODUCTS (30 штук)
        # ============================================================
        self.stdout.write('Creating 30 products...')

        products_data = [
            # Стоечные серверы
            ('Dell PowerEdge R750xs 2U', 'DEL-R750XS', 'Стоечные серверы', 'Dell',
             Decimal('485000'), Decimal('520000'), 'new', 8,
             'Сервер Dell PowerEdge R750xs 2U. Intel Xeon Silver 4314 2.4GHz 16C/32T, 32GB DDR4, 480GB SSD SATA. Идеален для виртуализации и баз данных.',
             'Мощный 2U сервер для корпоративных задач'),
            ('HPE ProLiant DL380 Gen10 Plus', 'HPE-DL380G10P', 'Стоечные серверы', 'HP Enterprise',
             Decimal('395000'), Decimal('450000'), 'new', 5,
             'HP Enterprise ProLiant DL380 Gen10 Plus с Intel Xeon Gold 5318Y, 64GB DDR4, двумя БП по 800Вт. Надёжный выбор для дата-центров.',
             'Флагманский 2U сервер HPE'),
            ('Supermicro SuperServer 1029P-MTR', 'SMC-1029PMTR', 'Стоечные серверы', 'Supermicro',
             Decimal('320000'), None, 'new', 3,
             'Компактный 1U двухпроцессорный сервер Supermicro. Поддержка до 2TB DDR4 ECC, 8x 2.5" hot-swap.',
             'Компактный 1U двухпроцессорный сервер'),
            ('Dell PowerEdge R740 2U (Б/У)', 'DEL-R740-REF', 'Стоечные серверы', 'Dell',
             Decimal('185000'), Decimal('380000'), 'refurbished', 12,
             'Восстановленный Dell PowerEdge R740. 2x Intel Xeon Gold 6148, 128GB DDR4, 4x 1.2TB SAS. Полная диагностика и гарантия 12 месяцев.',
             'Восстановленный сервер с гарантией'),
            ('Lenovo ThinkSystem SR650 V2', 'LEN-SR650V2', 'Стоечные серверы', 'Lenovo',
             Decimal('410000'), None, 'new', 6,
             'Универсальный 2U сервер Lenovo ThinkSystem SR650 V2 с поддержкой до 2 процессоров Intel Xeon Scalable 3-го поколения.',
             'Универсальный 2U сервер Lenovo'),

            # Башенные серверы
            ('Dell PowerEdge T550 Tower', 'DEL-T550', 'Башенные серверы', 'Dell',
             Decimal('295000'), Decimal('340000'), 'new', 4,
             'Башенный сервер Dell PowerEdge T550 для малого и среднего бизнеса. Тихая работа, простое обслуживание.',
             'Башенный сервер для SMB'),
            ('Lenovo ThinkSystem ST650 V2', 'LEN-ST650V2', 'Башенные серверы', 'Lenovo',
             Decimal('255000'), None, 'new', 7,
             'Мощный башенный сервер Lenovo ThinkSystem ST650 V2 с двумя процессорами и расширенными возможностями хранения.',
             'Мощный башенный сервер'),
            ('HPE ProLiant ML350 Gen10', 'HPE-ML350G10', 'Башенные серверы', 'HP Enterprise',
             Decimal('275000'), Decimal('310000'), 'new', 5,
             'Надёжный башенный сервер HPE ML350 Gen10 с возможностью конвертации в стоечный формат.',
             'Универсальный башенный/стоечный сервер'),

            # Процессоры
            ('Intel Xeon Gold 6348 2.6GHz 28C/56T', 'INT-6348', 'Процессоры', 'Intel',
             Decimal('142000'), Decimal('165000'), 'new', 15,
             'Серверный процессор Intel Xeon Gold 6348, 28 ядер, 56 потоков, TDP 235W. Socket LGA4189.',
             'Процессор Intel Xeon Gold 3-го поколения'),
            ('AMD EPYC 7543 2.8GHz 32C/64T', 'AMD-7543', 'Процессоры', 'AMD',
             Decimal('198000'), None, 'new', 10,
             'Серверный процессор AMD EPYC 7543 Milan, 32 ядра, 64 потока, L3 кэш 256MB. Socket SP3.',
             'Высокопроизводительный AMD EPYC'),
            ('Intel Xeon Silver 4314 2.4GHz 16C/32T', 'INT-4314', 'Процессоры', 'Intel',
             Decimal('68000'), Decimal('75000'), 'new', 20,
             'Серверный процессор Intel Xeon Silver 4314, 16 ядер, 32 потока, TDP 135W.',
             'Оптимальный Xeon Silver'),
            ('AMD EPYC 7313 3.0GHz 16C/32T', 'AMD-7313', 'Процессоры', 'AMD',
             Decimal('89000'), None, 'new', 12,
             'Процессор AMD EPYC 7313 Milan для однопроцессорных серверов. 16 ядер, 128MB L3.',
             'AMD EPYC для 1P серверов'),

            # Оперативная память
            ('Samsung DDR4 ECC RDIMM 64GB 3200MHz', 'SAM-64G-3200', 'Оперативная память', 'Samsung',
             Decimal('18500'), Decimal('22000'), 'new', 40,
             'Модуль серверной памяти Samsung 64GB DDR4 ECC Registered DIMM, 3200MHz, CL22.',
             'Серверная память 64GB DDR4'),
            ('Samsung DDR4 ECC RDIMM 32GB 3200MHz', 'SAM-32G-3200', 'Оперативная память', 'Samsung',
             Decimal('8900'), Decimal('11000'), 'new', 60,
             'Модуль серверной памяти Samsung 32GB DDR4 ECC Registered DIMM, 3200MHz.',
             'Серверная память 32GB DDR4'),
            ('Kingston DDR4 ECC UDIMM 16GB 3200MHz', 'KST-16G-3200', 'Оперативная память', 'Kingston',
             Decimal('4500'), None, 'new', 80,
             'Модуль памяти Kingston 16GB DDR4 ECC Unbuffered для однопроцессорных серверов.',
             'ECC память для tower-серверов'),

            # Жёсткие диски и SSD
            ('Samsung PM9A3 3.84TB NVMe U.2', 'SAM-PM9A3-4T', 'Жёсткие диски и SSD', 'Samsung',
             Decimal('45000'), Decimal('52000'), 'new', 25,
             'Серверный NVMe SSD Samsung PM9A3, 3.84TB, U.2, PCIe 4.0. Ресурс записи 1 DWPD.',
             'Ёмкий NVMe SSD для серверов'),
            ('Seagate Exos X18 18TB SAS 12Gb/s', 'SEA-X18-18T', 'Жёсткие диски и SSD', 'Seagate',
             Decimal('28000'), Decimal('32000'), 'new', 35,
             'Серверный HDD Seagate Exos X18 18TB, SAS 12Gb/s, 7200RPM, 256MB кэш.',
             'Серверный HDD 18TB для СХД'),
            ('Samsung PM893 960GB SATA', 'SAM-PM893-1T', 'Жёсткие диски и SSD', 'Samsung',
             Decimal('12500'), None, 'new', 45,
             'Серверный SATA SSD Samsung PM893, 960GB, 2.5", SATA 6Gb/s. MTBF 2M часов.',
             'Надёжный SATA SSD для серверов'),
            ('WD Ultrastar DC HC560 20TB', 'WDC-HC560-20T', 'Жёсткие диски и SSD', 'Western Digital',
             Decimal('35000'), None, 'new', 18,
             'Серверный HDD WD Ultrastar DC HC560 20TB, SATA 6Gb/s, 7200RPM. Для архивного хранения.',
             'HDD 20TB для архивов'),

            # Коммутаторы
            ('Cisco Catalyst 9300-48P', 'CIS-C9300-48P', 'Коммутаторы', 'Cisco',
             Decimal('285000'), Decimal('320000'), 'new', 6,
             'Управляемый коммутатор Cisco Catalyst 9300 с 48 портами PoE+, 4x 10G SFP+ uplink.',
             'Корпоративный коммутатор PoE+'),
            ('MikroTik CRS326-24G-2S+RM', 'MKT-CRS326', 'Коммутаторы', 'MikroTik',
             Decimal('18500'), None, 'new', 15,
             'Управляемый коммутатор MikroTik CRS326, 24 порта GbE, 2x SFP+ 10G. RouterOS/SwOS.',
             'Доступный 10G коммутатор'),

            # NAS
            ('Synology RackStation RS1221+', 'SYN-RS1221P', 'NAS-хранилища', 'Synology',
             Decimal('89000'), Decimal('98000'), 'new', 8,
             'Стоечная NAS Synology RS1221+ с 8 отсеками, AMD Ryzen V1500B, 4GB DDR4 ECC.',
             'Стоечная NAS для бизнеса'),
            ('Synology DiskStation DS1621+', 'SYN-DS1621P', 'NAS-хранилища', 'Synology',
             Decimal('65000'), None, 'new', 10,
             'Настольная NAS Synology DS1621+ с 6 отсеками для малого и среднего бизнеса.',
             'Настольная NAS 6 отсеков'),

            # ИБП
            ('APC Smart-UPS SRT 3000VA RM 230V', 'APC-SRT3000', 'Онлайн ИБП', 'APC',
             Decimal('125000'), Decimal('145000'), 'new', 10,
             'Онлайн ИБП APC Smart-UPS SRT 3000VA в стоечном исполнении 2U. Двойное преобразование.',
             'Онлайн ИБП 3000VA для серверов'),
            ('APC Smart-UPS SRT 5000VA RM 230V', 'APC-SRT5000', 'Онлайн ИБП', 'APC',
             Decimal('210000'), None, 'new', 4,
             'Мощный онлайн ИБП APC Smart-UPS SRT 5000VA с управлением по сети.',
             'Онлайн ИБП 5000VA'),

            # RAID-контроллеры
            ('Dell PERC H755 Adapter', 'DEL-H755', 'RAID-контроллеры', 'Dell',
             Decimal('32000'), None, 'new', 20,
             'RAID-контроллер Dell PERC H755 PCIe с поддержкой RAID 0,1,5,6,10,50,60. 8GB NV кэш.',
             'RAID-контроллер для PowerEdge'),

            # Блоки питания
            ('Dell 800W Hot-Plug PSU', 'DEL-PSU800', 'Блоки питания', 'Dell',
             Decimal('8500'), Decimal('11000'), 'new', 30,
             'Серверный блок питания Dell 800W с горячей заменой. 80 Plus Platinum.',
             'БП с горячей заменой'),

            # Серверные шкафы
            ('Шкаф серверный 42U 800x1000', 'CAB-42U-800', 'Напольные шкафы', None,
             Decimal('45000'), Decimal('52000'), 'new', 8,
             'Напольный серверный шкаф 42U глубиной 1000мм. Перфорированные двери, кабельные органайзеры.',
             'Серверный шкаф 42U'),

            # Маршрутизаторы
            ('MikroTik CCR2004-1G-12S+2XS', 'MKT-CCR2004', 'Маршрутизаторы', 'MikroTik',
             Decimal('42000'), None, 'new', 7,
             'Мощный маршрутизатор MikroTik CCR2004 с 12x SFP+ 10G и 2x SFP28 25G портами.',
             'Маршрутизатор 10G/25G'),
        ]

        all_products = []
        for (name, sku, cat_name, brand_name, price, old_price, condition,
             stock, desc, short_desc) in products_data:
            brand = all_brands.get(brand_name)
            category = all_categories.get(cat_name)
            if not category:
                continue
            p, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name, 'category': category, 'brand': brand,
                    'description': desc, 'short_description': short_desc,
                    'price': price, 'old_price': old_price,
                    'stock': stock, 'reserved': 0, 'condition': condition,
                    'warranty_months': 36 if condition == 'new' else 12,
                    'is_active': True,
                    'is_featured': random.random() > 0.5,
                }
            )
            all_products.append(p)
        self.stdout.write(f'  Products: {len(all_products)}')

        # Specifications
        spec_templates = {
            'Процессоры': [('Сокет', ['LGA4189', 'SP3']), ('TDP', ['135W', '165W', '225W', '235W'])],
            'Оперативная память': [('Тип', ['DDR4 ECC RDIMM', 'DDR4 ECC UDIMM']), ('Частота', ['3200MHz'])],
            'Стоечные серверы': [('Форм-фактор', ['1U', '2U']), ('Макс. память', ['1TB', '2TB', '4TB'])],
        }
        for p in all_products:
            if ProductSpecification.objects.filter(product=p).exists():
                continue
            cat_name = p.category.name
            specs = spec_templates.get(cat_name, [])
            for i, (spec_name, values) in enumerate(specs):
                ProductSpecification.objects.create(
                    product=p, name=spec_name, value=random.choice(values), order=i
                )

        # ============================================================
        # 5. SERVICE CATEGORIES & SERVICES (10)
        # ============================================================
        self.stdout.write('Creating services...')

        svc_cats_data = [
            ('Установка и монтаж', 'ustanovka-i-montazh', 'tools', 'Монтаж серверного оборудования в стойки и шкафы.'),
            ('Техническое обслуживание', 'tekhnicheskoe-obsluzhivanie', 'wrench', 'Профилактика и диагностика серверов.'),
            ('Консультации и аудит', 'konsultatsii-i-audit', 'clipboard-check', 'ИТ-консультации и аудит инфраструктуры.'),
            ('Настройка ПО', 'nastroika-po', 'code-slash', 'Установка и настройка серверного ПО.'),
            ('Аварийные работы', 'avariinye-raboty', 'lightning', 'Срочное восстановление после сбоев.'),
        ]
        svc_cats = {}
        for i, (name, slug, icon, desc) in enumerate(svc_cats_data):
            sc, _ = ServiceCategory.objects.get_or_create(
                slug=slug, defaults={'name': name, 'icon': icon, 'description': desc,
                                     'is_active': True, 'order': i}
            )
            svc_cats[name] = sc

        services_data = [
            ('Монтаж сервера в стойку', 'montazh-servera', svc_cats['Установка и монтаж'],
             'fixed', Decimal('5000'), None, 2,
             'Профессиональный монтаж сервера в 19" стойку с подключением питания и сети.'),
            ('Монтаж серверного шкафа', 'montazh-shkafa', svc_cats['Установка и монтаж'],
             'fixed', Decimal('15000'), None, 4,
             'Сборка и монтаж серверного шкафа, прокладка кабелей, установка PDU.'),
            ('Диагностика сервера', 'diagnostika-servera', svc_cats['Техническое обслуживание'],
             'fixed', Decimal('3000'), None, 1,
             'Полная диагностика серверного оборудования: тест CPU, RAM, дисков, сети.'),
            ('Профилактика оборудования', 'profilaktika', svc_cats['Техническое обслуживание'],
             'hourly', Decimal('0'), Decimal('2500'), 2,
             'Чистка от пыли, замена термопасты, проверка вентиляторов и БП.'),
            ('Замена компонентов', 'zamena-komponentov', svc_cats['Техническое обслуживание'],
             'fixed', Decimal('2000'), None, 1,
             'Замена процессора, памяти, дисков, БП с диагностикой совместимости.'),
            ('Аудит ИТ-инфраструктуры', 'audit-infrastruktury', svc_cats['Консультации и аудит'],
             'negotiable', Decimal('0'), None, 8,
             'Комплексный аудит серверной инфраструктуры с отчётом и рекомендациями.'),
            ('Установка и настройка ОС', 'ustanovka-os', svc_cats['Настройка ПО'],
             'fixed', Decimal('5000'), None, 2,
             'Установка Windows Server, Linux (Ubuntu, CentOS, RHEL), настройка обновлений и безопасности.'),
            ('Настройка RAID-массива', 'nastroika-raid', svc_cats['Настройка ПО'],
             'fixed', Decimal('4000'), None, 1,
             'Конфигурирование RAID-массивов на аппаратных и программных контроллерах.'),
            ('Восстановление данных', 'vosstanovlenie-dannykh', svc_cats['Аварийные работы'],
             'negotiable', Decimal('0'), None, 4,
             'Восстановление данных с повреждённых RAID-массивов, серверных дисков.'),
            ('Экстренный выезд и ремонт', 'ekstrennyi-remont', svc_cats['Аварийные работы'],
             'hourly', Decimal('0'), Decimal('5000'), 1,
             'Срочный выезд мастера в течение 2 часов для устранения аварийной ситуации.'),
        ]
        all_services = []
        for (name, slug, category, pricing, price, hourly, duration, desc) in services_data:
            s, _ = Service.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name, 'category': category, 'pricing_type': pricing,
                    'price': price, 'price_per_hour': hourly,
                    'duration_hours': duration, 'description': desc,
                    'short_description': desc[:100],
                    'is_active': True, 'is_popular': random.random() > 0.5,
                }
            )
            all_services.append(s)
        self.stdout.write(f'  Services: {len(all_services)}')

        # Technicians
        technicians = []
        for i, user in enumerate(tech_users):
            t, _ = Technician.objects.get_or_create(
                user=user,
                defaults={
                    'bio': f'Опытный специалист по серверному оборудованию. Стаж {5 + i * 3} лет.',
                    'experience_years': 5 + i * 3,
                    'certifications': 'Dell Certified, HPE ASE, Cisco CCNA',
                    'hourly_rate': Decimal('2500') + i * Decimal('500'),
                    'is_available': True, 'rating': Decimal('4.5') + Decimal(str(i * 0.2)),
                    'completed_orders': 20 + i * 15,
                }
            )
            t.specializations.set(random.sample(list(svc_cats.values()), k=min(3, len(svc_cats))))
            technicians.append(t)

        # ============================================================
        # 6. BLOG (10 posts)
        # ============================================================
        self.stdout.write('Creating blog...')

        blog_cats_data = [
            ('Обзоры оборудования', 'obzory'), ('Руководства', 'rukovodstva'),
            ('Новости компании', 'novosti'), ('Технологии', 'tekhnologii'),
        ]
        blog_cats = {}
        for name, slug in blog_cats_data:
            bc, _ = BlogCategory.objects.get_or_create(slug=slug, defaults={'name': name})
            blog_cats[name] = bc

        tags_data = [
            ('Dell', 'dell'), ('HP', 'hp'), ('Серверы', 'servery'), ('SSD', 'ssd'),
            ('RAID', 'raid'), ('Виртуализация', 'virtualizatsiya'),
            ('Безопасность', 'bezopasnost'), ('Linux', 'linux'),
        ]
        all_tags = []
        for name, slug in tags_data:
            tag, _ = Tag.objects.get_or_create(slug=slug, defaults={'name': name})
            all_tags.append(tag)

        posts_data = [
            ('Серверные тренды 2026: что изменилось', blog_cats['Технологии'],
             'Обзор главных трендов в серверной индустрии в 2026 году: DDR5, PCIe 5.0, CXL.',
             '<p>Серверный рынок в 2026 году претерпел значительные изменения. Переход на DDR5 стал массовым, а PCIe 5.0 теперь стандарт для NVMe SSD.</p><p>Технология CXL (Compute Express Link) позволяет создавать пулы памяти, доступные нескольким серверам одновременно.</p><h3>Основные тренды</h3><ul><li>DDR5 — стандарт для новых платформ</li><li>PCIe 5.0 — удвоение пропускной способности</li><li>CXL 2.0 — общая память</li><li>ARM-серверы — рост доли рынка</li></ul>'),
            ('Обзор NVMe SSD Samsung PM9A3 для серверов', blog_cats['Обзоры оборудования'],
             'Подробный обзор серверного NVMe SSD Samsung PM9A3: производительность, надёжность, цена.',
             '<p>Samsung PM9A3 — один из самых популярных серверных NVMe SSD. Мы протестировали модель на 3.84TB в реальных серверных нагрузках.</p><h3>Результаты тестов</h3><p>Последовательное чтение: 6900 MB/s<br>Последовательная запись: 4100 MB/s<br>Случайное чтение (4K): 1000K IOPS<br>Случайная запись (4K): 180K IOPS</p>'),
            ('Как выбрать сервер для малого бизнеса', blog_cats['Руководства'],
             'Пошаговое руководство по выбору первого сервера для SMB: от задач до конфигурации.',
             '<p>Выбор первого сервера — важный шаг для любого бизнеса. В этой статье разберём, на что обращать внимание.</p><h3>Шаг 1: Определите задачи</h3><p>Файловый сервер, почта, 1С, виртуализация — каждая задача требует разных ресурсов.</p><h3>Шаг 2: Выберите форм-фактор</h3><p>Tower — для офиса без серверной. Rack — если есть стойка или шкаф.</p>'),
            ('Настройка RAID на контроллерах Dell PERC', blog_cats['Руководства'],
             'Пошаговая инструкция по настройке RAID 1, 5, 6, 10 на контроллерах Dell PERC H755.',
             '<p>RAID-массивы обеспечивают отказоустойчивость хранения данных. Рассмотрим настройку на Dell PERC H755.</p><h3>RAID 1 (Зеркало)</h3><p>Минимум 2 диска. Полное дублирование. Идеально для ОС.</p><h3>RAID 5</h3><p>Минимум 3 диска. Распределённая чётность. Оптимален для файловых серверов.</p>'),
            ('ServerPro расширяет склад в Санкт-Петербурге', blog_cats['Новости компании'],
             'Мы открыли новый складской комплекс площадью 2000 м2 для ускорения доставки по СЗФО.',
             '<p>Рады сообщить, что ServerPro открыл новый складской комплекс в Санкт-Петербурге. Площадь склада — 2000 м2, что позволит хранить более 5000 единиц оборудования.</p><p>Теперь доставка по Санкт-Петербургу — от 4 часов, по СЗФО — от 1 дня.</p>'),
            ('VMware vs Proxmox: что выбрать в 2026', blog_cats['Технологии'],
             'Сравнение платформ виртуализации VMware vSphere и Proxmox VE: функции, цены, экосистема.',
             '<p>После изменения лицензионной политики VMware by Broadcom многие ищут альтернативы. Proxmox VE — главный претендент.</p><h3>VMware vSphere</h3><p>Зрелая платформа, богатая экосистема, высокая цена.</p><h3>Proxmox VE</h3><p>Открытый код, KVM + LXC, бесплатная базовая версия.</p>'),
            ('Топ-5 серверных процессоров 2026 года', blog_cats['Обзоры оборудования'],
             'Рейтинг лучших серверных процессоров Intel Xeon и AMD EPYC по соотношению цена/производительность.',
             '<p>Выбор процессора определяет производительность сервера на годы вперёд. Составили рейтинг лучших CPU.</p><ol><li>AMD EPYC 9354 — лучший по ядрам/доллар</li><li>Intel Xeon Gold 6448Y — оптимальный баланс</li><li>AMD EPYC 7543 — отличный выбор для HPC</li><li>Intel Xeon Silver 4416+ — бюджетный лидер</li><li>AMD EPYC 7313 — для 1P серверов</li></ol>'),
            ('Резервное копирование: стратегия 3-2-1', blog_cats['Руководства'],
             'Объясняем стратегию резервного копирования 3-2-1 и как её реализовать на практике.',
             '<p>Стратегия 3-2-1 — золотой стандарт резервного копирования.</p><h3>Правило 3-2-1</h3><ul><li><strong>3</strong> копии данных</li><li><strong>2</strong> типа носителей</li><li><strong>1</strong> копия offsite</li></ul><p>Рассмотрим реализацию с помощью Veeam Backup и Synology NAS.</p>'),
            ('Обзор Synology RS1221+ для SMB', blog_cats['Обзоры оборудования'],
             'Детальный обзор стоечной NAS Synology RS1221+: возможности, производительность, DSM 7.',
             '<p>Synology RS1221+ — компактная стоечная NAS для малого и среднего бизнеса. 8 отсеков, AMD Ryzen, ECC память.</p><h3>Характеристики</h3><p>CPU: AMD Ryzen V1500B<br>RAM: 4GB DDR4 ECC (до 32GB)<br>Отсеки: 8x 3.5" SATA<br>Сеть: 4x GbE</p>'),
            ('Как защитить сервер от ransomware', blog_cats['Руководства'],
             'Практические рекомендации по защите серверной инфраструктуры от программ-вымогателей.',
             '<p>Атаки программ-вымогателей — одна из главных угроз для бизнеса. Разберём меры защиты.</p><h3>Основные меры</h3><ol><li>Регулярные бэкапы по стратегии 3-2-1</li><li>Сегментация сети</li><li>Обновление ПО и патчи</li><li>Многофакторная аутентификация</li><li>Обучение сотрудников</li></ol>'),
        ]
        all_posts = []
        for i, (title, category, excerpt, content) in enumerate(posts_data):
            p, created = Post.objects.get_or_create(
                title=title,
                defaults={
                    'category': category, 'author': admin, 'excerpt': excerpt,
                    'content': content, 'status': 'published',
                    'is_featured': i < 3,
                    'views_count': random.randint(50, 2000),
                    'published_at': now - timedelta(days=random.randint(1, 90)),
                }
            )
            if created:
                p.tags.set(random.sample(all_tags, k=random.randint(2, 4)))
            all_posts.append(p)
        self.stdout.write(f'  Posts: {len(all_posts)}')

        # Comments
        comments_texts = [
            'Отличная статья, спасибо!', 'Очень полезно, давно искал такую информацию.',
            'Подскажите, а для виртуализации какой RAID лучше?',
            'Мы на PM9A3 перешли полгода назад — разница огромная.',
            'Хотелось бы больше про Proxmox почитать.',
            'Спасибо за подробный обзор!', 'А что насчёт AMD EPYC Genoa?',
            'Используем Synology уже 3 года — полёт нормальный.',
        ]
        for post in all_posts[:6]:
            if post.comments.exists():
                continue
            for _ in range(random.randint(1, 3)):
                Comment.objects.create(
                    post=post, user=random.choice(clients),
                    content=random.choice(comments_texts),
                    is_approved=True,
                )

        # ============================================================
        # 7. PROMOTIONS & PROMO CODES
        # ============================================================
        self.stdout.write('Creating promotions...')

        promos = [
            ('Весенняя распродажа серверов', 'vesennyaya-rasprodazha', 'discount',
             'Скидки до 15% на серверы Dell и HPE до конца марта!',
             '<p>Весенняя распродажа серверного оборудования! Скидки до 15% на серверы Dell PowerEdge и HPE ProLiant.</p>',
             15, None),
            ('Бесплатная установка при заказе от 200 000 руб.', 'besplatnaya-ustanovka', 'bundle',
             'Закажите сервер от 200 000 руб. и получите бесплатный монтаж в стойку.',
             '<p>При заказе серверного оборудования на сумму от 200 000 рублей — бесплатный монтаж в стойку и первичная настройка.</p>',
             None, None),
            ('Скидка 20% на обслуживание', 'skidka-na-obsluzhivanie', 'service',
             'Заключите договор на ТО и получите скидку 20% на первые 3 месяца.',
             '<p>Заключите годовой контракт на техническое обслуживание серверной инфраструктуры со скидкой 20% на первые 3 месяца.</p>',
             20, None),
        ]
        all_promos = []
        for (title, slug, ptype, short, desc, percent, amount) in promos:
            pr, _ = Promotion.objects.get_or_create(
                slug=slug,
                defaults={
                    'title': title, 'type': ptype, 'short_description': short,
                    'description': desc, 'discount_percent': percent,
                    'discount_amount': amount,
                    'start_date': now - timedelta(days=10),
                    'end_date': now + timedelta(days=60),
                    'is_active': True, 'is_featured': True,
                }
            )
            all_promos.append(pr)

        # Promo codes
        codes_data = [
            ('SPRING2026', 'percent', Decimal('10'), Decimal('10000'), None),
            ('WELCOME', 'percent', Decimal('5'), Decimal('0'), None),
            ('SAVE5000', 'fixed', Decimal('5000'), Decimal('50000'), Decimal('5000')),
            ('VIP15', 'percent', Decimal('15'), Decimal('20000'), Decimal('50000')),
        ]
        for (code, ctype, value, min_amount, max_disc) in codes_data:
            PromoCode.objects.get_or_create(
                code=code,
                defaults={
                    'promotion': all_promos[0] if ctype == 'percent' else None,
                    'type': ctype, 'value': value,
                    'min_order_amount': min_amount,
                    'max_discount_amount': max_disc,
                    'usage_limit': 100, 'times_used': random.randint(0, 20),
                    'start_date': now - timedelta(days=10),
                    'end_date': now + timedelta(days=90),
                    'is_active': True,
                }
            )

        # Banners
        banners = [
            ('Серверы Dell со скидкой до 15%', 'home_top'),
            ('Бесплатная доставка от 50 000 руб.', 'home_middle'),
        ]
        for title, pos in banners:
            Banner.objects.get_or_create(
                title=title,
                defaults={
                    'position': pos, 'is_active': True, 'order': 0,
                    'start_date': now - timedelta(days=10),
                    'end_date': now + timedelta(days=90),
                }
            )

        # ============================================================
        # 8. ORDERS
        # ============================================================
        self.stdout.write('Creating orders...')

        order_count = 0
        # Distribute orders over the last 45 days for chart data
        order_dates = sorted([
            now - timedelta(days=random.randint(0, 45))
            for _ in range(20)
        ])
        date_idx = 0

        for client in clients[:6]:
            for _ in range(random.randint(1, 3)):
                items = random.sample(all_products, k=random.randint(1, 4))
                subtotal = sum(p.price * random.randint(1, 2) for p in items)
                delivery = Decimal('0') if subtotal >= 50000 else Decimal('500')

                order_date = order_dates[date_idx % len(order_dates)]
                date_idx += 1

                status = random.choice(['pending', 'confirmed', 'processing',
                                        'shipped', 'delivered', 'completed'])
                # Recent orders more likely pending
                if (now - order_date).days < 3:
                    status = random.choice(['pending', 'confirmed'])

                order = Order(
                    user=client,
                    status=status,
                    payment_status='paid' if status in ('shipped', 'delivered', 'completed') else random.choice(['pending', 'paid']),
                    payment_method=random.choice(['card', 'invoice', 'invoice']),
                    delivery_city=random.choice(cities),
                    delivery_address=f'{random.choice(streets)}, д. {random.randint(1, 100)}',
                    delivery_postal_code=f'{random.randint(100, 199)}0{random.randint(10, 99)}',
                    contact_name=f'{client.first_name} {client.last_name}',
                    contact_phone=client.phone,
                    contact_email=client.email,
                    subtotal=subtotal,
                    delivery_cost=delivery,
                    discount=Decimal('0'),
                    total=subtotal + delivery,
                )
                order.save()
                # Override auto_now_add to set historical date
                Order.objects.filter(pk=order.pk).update(created_at=order_date)

                for product in items:
                    qty = random.randint(1, 2)
                    OrderItem.objects.create(
                        order=order, product=product,
                        quantity=qty, price=product.price,
                    )

                OrderStatusHistory.objects.create(
                    order=order, old_status='', new_status='pending',
                    changed_by=admin, comment='Заказ создан',
                )
                # Override history date too
                OrderStatusHistory.objects.filter(order=order, new_status='pending').update(
                    created_at=order_date
                )
                if order.status != 'pending':
                    OrderStatusHistory.objects.create(
                        order=order, old_status='pending',
                        new_status=order.status, changed_by=manager,
                    )
                    OrderStatusHistory.objects.filter(
                        order=order, new_status=order.status
                    ).update(created_at=order_date + timedelta(hours=random.randint(1, 48)))

                order_count += 1
        self.stdout.write(f'  Orders: {order_count}')

        # ============================================================
        # 9. SERVICE REQUESTS
        # ============================================================
        self.stdout.write('Creating service requests...')

        sr_count = 0
        for client in clients[:5]:
            for _ in range(random.randint(1, 2)):
                service = random.choice(all_services)
                tech = random.choice(technicians) if random.random() > 0.3 else None
                status = random.choice(['pending', 'confirmed', 'assigned',
                                        'in_progress', 'completed'])
                if not tech and status in ('assigned', 'in_progress', 'completed'):
                    tech = technicians[0]

                sr = ServiceRequest(
                    user=client, service=service,
                    technician=tech,
                    status=status,
                    urgency=random.choice(['normal', 'normal', 'urgent', 'emergency']),
                    title=f'Заявка: {service.name}',
                    description=f'Требуется {service.name.lower()} для нашего оборудования.',
                    contact_name=f'{client.first_name} {client.last_name}',
                    contact_phone=client.phone,
                    contact_email=client.email,
                    address_city=random.choice(cities),
                    address_street=f'{random.choice(streets)}, д. {random.randint(1, 100)}',
                    preferred_date=(now + timedelta(days=random.randint(1, 14))).date(),
                    preferred_time_from='09:00',
                    preferred_time_to='18:00',
                    estimated_cost=service.price if service.price else Decimal('5000'),
                )
                sr.save()

                ServiceRequestHistory.objects.create(
                    request=sr, old_status='', new_status='pending',
                    changed_by=admin, comment='Заявка создана',
                )
                if status != 'pending':
                    ServiceRequestHistory.objects.create(
                        request=sr, old_status='pending',
                        new_status=status, changed_by=manager,
                    )
                sr_count += 1
        self.stdout.write(f'  Service requests: {sr_count}')

        # ============================================================
        # 10. REVIEWS
        # ============================================================
        self.stdout.write('Creating reviews...')

        review_data = [
            ('Отличный сервер для виртуализации', 5,
             'Купили Dell R750xs для VMware кластера. Работает безупречно уже 3 месяца.',
             'Производительность, надёжность, тихая работа', 'Высокая цена'),
            ('Хорошее решение за свои деньги', 4,
             'Взяли восстановленный R740 для тестовой среды. Пришёл в отличном состоянии.',
             'Цена, комплектация, состояние', 'Гарантия только 12 месяцев'),
            ('Супер процессор AMD EPYC', 5,
             'EPYC 7543 показывает отличные результаты в многопоточных задачах.',
             '32 ядра, энергоэффективность', 'Дороговат'),
            ('Надёжная память Samsung', 5,
             'Используем Samsung ECC RDIMM уже в десятках серверов — ни одного сбоя.',
             'Надёжность, совместимость', 'Нет'),
            ('NAS Synology — лучший выбор', 4,
             'RS1221+ работает как часы. DSM 7 очень удобная система.',
             'DSM, приложения, надёжность', 'Хотелось бы 2.5GbE порты'),
            ('Быстрый SSD Samsung PM9A3', 5,
             'Перешли с SATA SSD на NVMe PM9A3 — разница колоссальная.',
             'Скорость, ресурс, надёжность', 'Цена выше SATA'),
            ('Коммутатор MikroTik — отличная цена', 4,
             'CRS326 за свои деньги — просто бомба. 10G uplink, полноценное управление.',
             'Цена, функционал, RouterOS', 'Документация на английском'),
            ('ИБП APC SRT3000 — must have', 5,
             'Онлайн ИБП с чистым синусом. Защитил от 3 отключений за месяц.',
             'Двойное преобразование, управление', 'Тяжёлый'),
            ('Хороший башенный сервер', 4,
             'T550 отлично подходит для офиса без серверной. Тихий, компактный.',
             'Тихая работа, простое обслуживание', 'Ограниченная расширяемость'),
            ('Seagate Exos — рабочая лошадка', 4,
             'Exos X18 в составе RAID6 работает стабильно. 18TB — оптимальный объём.',
             'Объём, надёжность, цена за TB', 'Нагрев при нагрузке'),
        ]
        rev_count = 0
        used_pairs = set(Review.objects.values_list('user_id', 'product_id'))
        for i, (title, rating, content, pros, cons) in enumerate(review_data):
            client = clients[i % len(clients)]
            product = all_products[i % len(all_products)]
            if (client.id, product.id) in used_pairs:
                continue
            Review.objects.create(
                user=client, product=product, rating=rating,
                title=title, content=content, pros=pros, cons=cons,
                quality_rating=random.randint(4, 5),
                value_rating=random.randint(3, 5),
                is_approved=True, is_verified_purchase=random.random() > 0.3,
                helpful_count=random.randint(0, 20),
                not_helpful_count=random.randint(0, 3),
            )
            used_pairs.add((client.id, product.id))
            rev_count += 1
        self.stdout.write(f'  Reviews: {rev_count}')

        # ============================================================
        # 11. NOTIFICATIONS
        # ============================================================
        self.stdout.write('Creating notifications...')
        notif_templates = [
            ('order', 'Заказ подтверждён', 'Ваш заказ подтверждён и передан в обработку.'),
            ('order', 'Заказ отправлен', 'Ваш заказ отправлен. Ожидайте доставку.'),
            ('service', 'Мастер назначен', 'На вашу заявку назначен мастер.'),
            ('promo', 'Новая акция!', 'Скидки до 15% на серверы Dell и HPE.'),
            ('system', 'Добро пожаловать!', 'Спасибо за регистрацию на ServerPro B2B.'),
        ]
        for client in clients[:4]:
            for ntype, title, msg in random.sample(notif_templates, k=3):
                Notification.objects.get_or_create(
                    user=client, title=title,
                    defaults={'type': ntype, 'message': msg, 'is_read': random.random() > 0.5}
                )

        # Admin notifications
        for ntype, title, msg in notif_templates[:3]:
            Notification.objects.get_or_create(
                user=admin, title=title,
                defaults={'type': ntype, 'message': msg, 'is_read': False}
            )

        # ============================================================
        # 12. WISHLIST
        # ============================================================
        for client in clients[:5]:
            wished = random.sample(all_products, k=random.randint(2, 5))
            for product in wished:
                Wishlist.objects.get_or_create(user=client, product=product)

        # ============================================================
        # 13. DASHBOARD SETTINGS
        # ============================================================
        settings = DashboardSettings.get_settings()
        settings.site_name = 'Интернет-магазин комплектующих для серверов'
        settings.site_description = 'Профессиональные IT-решения для бизнеса. Серверное и сетевое оборудование, комплектующие и услуги по установке.'
        settings.email = 'serverpro@gmail.com'
        settings.phone = '+7 (950) 211-08-51'
        settings.address = 'г. Курск, ул. Ленина, 76, офис 312'
        settings.telegram_url = 'https://t.me/serverpro'
        settings.whatsapp = '79502110851'
        settings.meta_title = 'Интернет-магазин комплектующих для серверов'
        settings.meta_description = 'Интернет-магазин серверного и сетевого оборудования. Доставка по России, гарантия, техподдержка 24/7.'
        settings.min_order_amount = Decimal('5000')
        settings.free_delivery_amount = Decimal('50000')
        settings.delivery_cost = Decimal('500')

        # Логотип не создаётся автоматически — название сайта рендерится текстом в шапке.
        # Загрузить кастомный логотип можно через админ-панель (Настройки сайта).
        from PIL import Image, ImageDraw, ImageFont
        from io import BytesIO
        from django.core.files.base import ContentFile
        if settings.logo:
            settings.logo.delete(save=False)

        # Favicon
        fav_size = 64
        fav_img = Image.new('RGBA', (fav_size, fav_size), (0, 0, 0, 0))
        fav_draw = ImageDraw.Draw(fav_img)
        fav_draw.rounded_rectangle(
            [4, 4, 60, 60], radius=14, fill=(37, 99, 235)
        )
        try:
            fav_font = ImageFont.truetype("arialbd.ttf", 36)
        except (IOError, OSError):
            fav_font = ImageFont.load_default()
        bbox = fav_draw.textbbox((0, 0), "S", font=fav_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        fav_draw.text(
            ((fav_size - tw) // 2, (fav_size - th) // 2 - 2),
            "S", fill=(255, 255, 255), font=fav_font
        )
        fav_buf = BytesIO()
        fav_img.save(fav_buf, format='PNG')
        settings.favicon.save('favicon.png', ContentFile(fav_buf.getvalue()), save=False)

        settings.save()

        self.stdout.write(self.style.SUCCESS('\nDone! Test data created successfully.'))
        self.stdout.write(f'\nAccounts:')
        self.stdout.write(f'  Admin:      admin@serverpro.ru / admin123')
        self.stdout.write(f'  Manager:    manager@serverpro.ru / manager123')
        self.stdout.write(f'  Technician: tech1@serverpro.ru / tech123')
        self.stdout.write(f'  Client:     ivanov@example.com / client123')
        self.stdout.write(f'\nPromo codes: SPRING2026, WELCOME, SAVE5000, VIP15')
