from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import MaxValueValidator, MinValueValidator
# 自己写的小脚本 用于生成邀请码
from .tools import get_long_random_string, get_short_random_string
from django.conf import settings

import datetime

METHOD_CHOICES = (
    ('aes-256-cfb', 'aes-256-cfb'),
    ('rc4-md5', 'rc4-md5'),
    ('salsa20', 'salsa20'),
    ('aes-128-ctr', 'aes-128-ctr'),
)
STATUS_CHOICES = (
    ('好用', '好用'),
    ('维护', '维护'),
    ('坏了', '坏了'),
)

PROTOCOL_CHOICES = (
    ('auth_sha1_v4', 'auth_sha1_v4'),
    ('auth_aes128_md5', 'auth_aes128_md5'),
    ('auth_aes128_sha1', 'auth_aes128_sha1'),
    ('auth_chain_a', 'auth_chain_a'),
    ('origin', 'origin'),
)


OBFS_CHOICES = (
    ('plain', 'plain'),
    ('http_simple', 'http_simple'),
    ('http_post', 'http_post'),
    ('tls1.2_ticket_auth', 'tls1.2_ticket_auth'),
)

# Create your models here.


class User(AbstractUser):
    '''SS账户模型'''

    balance = models.DecimalField(
        '余额',
        decimal_places=2,
        max_digits=10,
        default=0,
        editable=False,
        null=True,
        blank=True,
    )

    invitecode = models.CharField(
        '邀请码',
        max_length=40,
    )

    # 最高等级限制为9级，和节点等级绑定
    level = models.PositiveIntegerField(
        '用户等级',
        default=0,
        validators=[
            MaxValueValidator(9),
            MinValueValidator(0),
        ]
    )

    level_expire_time = models.DateTimeField(
        '等级有效期',
        default=datetime.datetime.fromtimestamp(0),
        help_text='等级有效期',
    )

    def __str__(self):
        return self.username

    def get_expire_time(self):
        '''返回等级到期时间'''
        return self.level_expire_time

    class Meta(AbstractUser.Meta):
        verbose_name = '用户'


class Node(models.Model):
    '''线路节点'''

    node_id = models.IntegerField('节点id', unique=True,)

    name = models.CharField('名字', max_length=32,)

    server = models.CharField('服务器IP', max_length=128,)

    method = models.CharField(
        '加密类型', default='aes-256-cfb', max_length=32, choices=METHOD_CHOICES,)

    custom_method = models.SmallIntegerField(
        '自定义加密',
        choices=(
            (0, 0),
            (1, 1)),
        default=0,
    )
    traffic_rate = models.FloatField(
        '流量比例',
        default=1.0
    )

    protocol = models.CharField(
        '协议', default='origin', max_length=32, choices=PROTOCOL_CHOICES,)

    obfs = models.CharField(
        '混淆', default='plain', max_length=32, choices=OBFS_CHOICES,)

    info = models.CharField('节点说明', max_length=1024, blank=True, null=True,)

    status = models.CharField(
        '状态', max_length=32, default='ok', choices=STATUS_CHOICES,)

    level = models.PositiveIntegerField(
        '节点等级',
        default=0,
        validators=[
            MaxValueValidator(9),
            MinValueValidator(0),
        ]
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']
        verbose_name_plural = '节点'
        db_table = 'ss_node'


class NodeInfoLog(models.Model):
    '''节点负载记录'''

    node_id = models.IntegerField('节点id', blank=False, null=False)

    uptime = models.FloatField('更新时间', blank=False, null=False)

    load = models.CharField('负载', max_length=32, blank=False, null=False)

    log_time = models.IntegerField('日志时间', blank=False, null=False)

    def __str__(self):
        return str(self.node_id)

    class Meta:
        verbose_name_plural = '节点日志'
        db_table = 'ss_node_info_log'
        ordering = ('-log_time',)


class NodeOnlineLog(models.Model):
    '''节点在线记录'''

    node_id = models.IntegerField('节点id', blank=False, null=False)

    online_user = models.IntegerField('在线人数', blank=False, null=False)

    log_time = models.IntegerField('日志时间', blank=False, null=False)

    def __str__(self):
        return '节点：{}'.format(self.node_id)

    class Meta:
        verbose_name_plural = '节点在线记录'
        db_table = 'ss_node_online_log'


class InviteCode(models.Model):
    '''邀请码'''

    type = models.IntegerField(
        '类型',
        choices=((1, '公开'), (0, '不公开')),
        default=0,
    )

    code = models.CharField(
        '邀请码',
        primary_key=True,
        blank=True,
        max_length=40,
        default=get_long_random_string
    )

    time_created = models.DateTimeField(
        '创建时间',
        editable=False,
        auto_now_add=True
    )

    def clean(self):
        # 保证邀请码不会重复
        code_length = len(self.code or '')
        if 0 < code_length < 16:
            self.code = '{}{}'.format(
                self.code,
                get_long_random_string()
            )
        else:
            self.code = None

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):

        # 重写save方法，在包存前执行我们写的clean方法
        self.clean()
        return super(InviteCode, self).save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return str(self.code)

    class Meta:
        verbose_name_plural = '邀请码'
        ordering = ('-time_created',)


class Aliveip(models.Model):
    '''节点在线ip'''

    node_id = models.ForeignKey(
        Node,
        related_name='alive_node_id',
        on_delete=models.CASCADE,
        blank=True, null=True
    )

    user_name = models.CharField(
        '用户名',
        max_length=50,
        blank=True, null=True)

    ip_address = models.GenericIPAddressField('在线ip')

    local = models.CharField(
        '归属地',
        max_length=128,
        blank=True, null=True
    )
    time = models.DateTimeField(
        '时间',
        editable=False,
        auto_now_add=True
    )

    def __str__(self):
        return self.ip_address

    class Meta:
        verbose_name_plural = '在线ip'
        ordering = ('-time',)


class Donate(models.Model):
    '''捐赠记录'''
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )

    time = models.DateTimeField(
        '捐赠时间',
        editable=False,
        auto_now_add=True
    )

    money = models.DecimalField(
        '捐赠金额',
        decimal_places=2,
        max_digits=10,
        default=0,
        null=True,
        blank=True,
    )

    def __str__(self):
        return str(self.money)

    class Meta:
        verbose_name_plural = '捐赠'
        ordering = ('-time',)


class MoneyCode(models.Model):
    '''充值码'''
    user = models.CharField(
        '用户名',
        max_length=128,
        blank=True,
        null=True,
    )

    time = models.DateTimeField(
        '捐赠时间',
        editable=False,
        auto_now_add=True
    )

    code = models.CharField(
        '充值码',
        unique=True,
        blank=True,
        max_length=40,
        default=get_long_random_string
    )

    number = models.DecimalField(
        '捐赠金额',
        decimal_places=2,
        max_digits=10,
        default=10,
        null=True,
        blank=True,
    )

    isused = models.BooleanField(
        '是否使用',
        default=False,
    )

    def clean(self):
        # 保证充值码不会重复
        code_length = len(self.code or '')
        if 0 < code_length < 12:
            self.code = '{}{}'.format(
                self.code,
                get_long_random_string()
            )
        else:
            self.code = get_long_random_string()

    def __str__(self):
        return self.code

    class Meta:
        verbose_name_plural = '充值码'
        ordering = ('isused',)


class Shop(models.Model):
    '''商品'''

    name = models.CharField(
        '商品描述',
        max_length=128,

    )

    transfer = models.BigIntegerField(
        '增加的流量',
        default=settings.GB
    )

    money = models.DecimalField(
        '金额',
        decimal_places=2,
        max_digits=10,
        default=0,
        null=True,
        blank=True,
    )

    level = models.PositiveIntegerField(
        '设置等级',
        default=0,
        validators=[
            MaxValueValidator(9),
            MinValueValidator(0),
        ]
    )

    days = models.PositiveIntegerField(
        '设置等级时间(天)',
        default=0,
        validators=[
            MaxValueValidator(365),
            MinValueValidator(1),
        ]
    )

    def __str__(self):
        return self.name

    def get_transfer_by_GB(self):
        '''增加的流量以GB的形式返回'''
        return '{}'.format(self.transfer / settings.GB)

    def get_days(self):
        '''返回增加的天数'''
        return '{}'.format(self.days)

    class Meta:
        verbose_name_plural = '商品'


class PurchaseHistory(models.Model):
    '''购买记录'''

    info = models.ForeignKey(Shop)

    user = models.CharField(
        '购买者',
        max_length=128,

    )

    purchtime = models.DateTimeField(
        '购买时间',
        editable=False,
        auto_now_add=True
    )

    def __str__(self):
        return self.user

    class Meta:
        verbose_name_plural = '购买记录'


class AlipayRecord(models.Model):
    '''充值流水单号记录'''

    info_code = models.CharField(
        '流水号',
        max_length=64,
        unique=True,
    )

    time = models.DateTimeField(
        '时间',
        auto_now_add=True
    )

    amount = models.DecimalField(
        '金额',
        decimal_places=2,
        max_digits=10,
        default=0,
        null=True,
        blank=True,
    )

    money_code = models.CharField(
        '充值码',
        max_length=64,
        unique=True,
    )

    def __str__(self):
        return self.info_code

    class Meta:
        verbose_name_plural = '支付宝转账记录'
        ordering = ('-time',)


class AlipayRequest(models.Model):
    '''支付宝申请记录'''

    username = models.CharField(
        '用户名',
        max_length=64,
        blank=False,
        null=False
    )

    info_code = models.CharField(
        '流水号',
        max_length=64,
        unique=True,
    )

    time = models.DateTimeField(
        '时间',
        auto_now_add=True
    )

    amount = models.DecimalField(
        '金额',
        decimal_places=2,
        max_digits=10,
        default=0,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.username

    class Meta:
        verbose_name_plural = '支付宝申请记录'
        ordering = ('-time',)
