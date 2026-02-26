"""
HomeMe - Real Estate Models
Модели для недвижимости: BI Group ЖК/Офисы и вторичный рынок.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class BIComplex(models.Model):
    """Жилые Комплексы BI Group"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bi_uuid = models.CharField("UUID из API", max_length=100, unique=True, db_index=True)
    name = models.CharField("Название", max_length=255)
    address = models.CharField("Адрес", max_length=500, blank=True)
    description = models.TextField(blank=True)
    latitude = models.FloatField("Широта", null=True, blank=True)
    longitude = models.FloatField("Долгота", null=True, blank=True)
    city_uuid = models.CharField("UUID Города", max_length=100, db_index=True, blank=True)
    class_name = models.CharField("Класс", max_length=100, blank=True)
    deadline = models.CharField("Срок сдачи", max_length=50, blank=True)
    min_price = models.DecimalField("Цена от", max_digits=15, decimal_places=2, null=True)
    min_area = models.FloatField("Площадь от", null=True, blank=True)
    max_area = models.FloatField("Площадь до", null=True, blank=True)
    url = models.URLField(blank=True)
    image_url = models.URLField("Фото", blank=True)
    features = models.JSONField("AI Теги", default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ЖК (Жилой)"
        verbose_name_plural = "ЖК (Жилые)"
        db_table = 'bi_complexes'
        ordering = ['-updated_at']

    def __str__(self):
        return self.name


class BIUnit(models.Model):
    """Квартиры в ЖК BI Group"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bi_uuid = models.CharField("UUID Юнита", max_length=100, unique=True, db_index=True)
    complex = models.ForeignKey(BIComplex, on_delete=models.CASCADE, related_name='units')
    room_count = models.IntegerField("Комнат", db_index=True)
    floor = models.IntegerField("Этаж")
    max_floor = models.IntegerField("Всего этажей", null=True)
    area = models.FloatField("Площадь")
    price = models.DecimalField("Базовая цена", max_digits=15, decimal_places=2)
    price_discount = models.DecimalField("Цена со скидкой", max_digits=15, decimal_places=2, null=True, blank=True)
    block_name = models.CharField("Блок/Секция", max_length=100, blank=True)
    deadline = models.CharField("Срок сдачи секции", max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    photos = models.JSONField("Фотографии", default=list, blank=True)

    class Meta:
        verbose_name = "Квартира"
        verbose_name_plural = "Квартиры"
        db_table = 'bi_units'
        indexes = [
            models.Index(fields=['price_discount', 'room_count']),
            models.Index(fields=['area']),
        ]

    def __str__(self):
        return f"{self.room_count}-комн. {self.area}м² в {self.complex.name}"

    @property
    def current_price(self):
        return self.price_discount if self.price_discount else self.price


class BICommercialComplex(models.Model):
    """Бизнес Центры и Коммерция BI Group"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bi_uuid = models.CharField("UUID из API", max_length=100, unique=True, db_index=True)
    name = models.CharField("Название", max_length=255)
    address = models.CharField("Адрес", max_length=500, blank=True)
    description = models.TextField(blank=True)
    latitude = models.FloatField("Широта", null=True, blank=True)
    longitude = models.FloatField("Долгота", null=True, blank=True)
    city_uuid = models.CharField("UUID Города", max_length=100, db_index=True, blank=True)
    class_name = models.CharField("Класс", max_length=100, blank=True)
    deadline = models.CharField("Срок сдачи", max_length=50, blank=True)
    min_price = models.DecimalField("Цена от", max_digits=15, decimal_places=2, null=True)
    min_area = models.FloatField("Площадь от", null=True, blank=True)
    max_area = models.FloatField("Площадь до", null=True, blank=True)
    url = models.URLField(blank=True)
    image_url = models.URLField("Фото", blank=True)
    features = models.JSONField("AI Теги", default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Коммерческий объект"
        verbose_name_plural = "Коммерческие объекты"
        db_table = 'bi_commercial_complexes'
        ordering = ['-updated_at']

    def __str__(self):
        return self.name


class BICommercialUnit(models.Model):
    """Офисы и помещения в Бизнес Центрах"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bi_uuid = models.CharField("UUID Юнита", max_length=100, unique=True, db_index=True)
    complex = models.ForeignKey(BICommercialComplex, on_delete=models.CASCADE, related_name='units')
    room_count = models.IntegerField("Помещений", db_index=True)
    floor = models.IntegerField("Этаж")
    max_floor = models.IntegerField("Всего этажей", null=True)
    area = models.FloatField("Площадь")
    price = models.DecimalField("Базовая цена", max_digits=15, decimal_places=2)
    price_discount = models.DecimalField("Цена со скидкой", max_digits=15, decimal_places=2, null=True, blank=True)
    block_name = models.CharField("Блок/Секция", max_length=100, blank=True)
    deadline = models.CharField("Срок сдачи секции", max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    photos = models.JSONField("Фотографии", default=list, blank=True)

    class Meta:
        verbose_name = "Офис/Помещение"
        verbose_name_plural = "Офисы/Помещения"
        db_table = 'bi_commercial_units'

    def __str__(self):
        return f"Офис {self.area}м² в {self.complex.name}"

    @property
    def current_price(self):
        return self.price_discount if self.price_discount else self.price


class SecondaryProperty(models.Model):
    """Объект вторичной недвижимости"""

    DEAL_TYPE_CHOICES = [
        ('sale', 'Продажа'),
        ('rent', 'Аренда'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    external_uuid = models.CharField("Внешний UUID", max_length=100, unique=True, null=True, blank=True)
    external_id = models.BigIntegerField("Внешний ID", null=True, blank=True)
    property_type = models.CharField("Тип объекта", max_length=50, null=True, blank=True)
    deal_type = models.CharField("Тип сделки", max_length=50, choices=DEAL_TYPE_CHOICES, null=True, blank=True)
    condition = models.CharField("Состояние", max_length=50, null=True, blank=True)
    repair = models.CharField("Ремонт", max_length=50, null=True, blank=True)
    construction_year = models.IntegerField("Год постройки", null=True, blank=True)
    source_url = models.URLField("Источник", blank=True)
    photos = models.JSONField("Фотографии", default=list, blank=True)
    title = models.CharField("Заголовок", max_length=200)
    description = models.TextField("Описание")
    address = models.CharField("Адрес", max_length=255)
    price = models.DecimalField("Цена (₸)", max_digits=12, decimal_places=0,
                                validators=[MinValueValidator(0)])
    rooms = models.IntegerField("Количество комнат",
                                validators=[MinValueValidator(0), MaxValueValidator(10)])
    area = models.FloatField("Площадь (м²)", validators=[MinValueValidator(0)])
    floor = models.IntegerField("Этаж", validators=[MinValueValidator(0)])
    total_floors = models.IntegerField("Всего этажей", validators=[MinValueValidator(1)])
    city = models.CharField("Город", max_length=50, null=True, blank=True)
    district = models.CharField("Район", max_length=100, null=True, blank=True)
    latitude = models.FloatField("Широта", null=True, blank=True)
    longitude = models.FloatField("Долгота", null=True, blank=True)
    owner_phone = models.CharField("Телефон владельца", max_length=20, blank=True)
    owner_name = models.CharField("Имя владельца", max_length=100, blank=True)
    has_parking = models.BooleanField("Парковка", default=False)
    has_balcony = models.BooleanField("Балкон", default=False)
    has_renovation = models.BooleanField("С ремонтом", default=False)
    image = models.ImageField("Фото", upload_to='properties/%Y/%m/', blank=True, null=True)
    is_active = models.BooleanField("Активно", default=True)
    is_verified = models.BooleanField("Проверено", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.IntegerField("Просмотры", default=0)

    class Meta:
        verbose_name = "Вторичная недвижимость"
        verbose_name_plural = "Вторичная недвижимость"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['city', 'rooms', 'price']),
            models.Index(fields=['is_active', '-created_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.price:,.0f} ₸"

    @property
    def price_per_sqm(self) -> float:
        if self.area > 0:
            return float(self.price) / self.area
        return 0.0

    def increment_views(self):
        """Увеличивает счётчик просмотров."""
        self.views_count += 1
        self.save(update_fields=['views_count'])
