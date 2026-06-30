from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, RegexValidator
from hcaptcha.fields import hCaptchaField


class RegisterForm(UserCreationForm):
    username = forms.CharField(
        label='Никнейм',
        max_length=30,
        widget=forms.TextInput(attrs={
            'placeholder': 'Придумайте никнейм',
            'autocomplete': 'username',
        })
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Минимум 8 символов',
            'autocomplete': 'new-password',
        })
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Повторите пароль',
            'autocomplete': 'new-password',
        })
    )
    agree_privacy = forms.BooleanField(
        label='',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'auth-checkbox'})
    )
    captcha = hCaptchaField(
        label='',
        error_messages={'required': 'Пожалуйста, подтвердите, что вы не робот'}
    )

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].validators.append(
            MinLengthValidator(3, message='Никнейм должен быть не менее 3 символов')
        )
        self.fields['username'].validators.append(
            RegexValidator(
                regex=r'^[\w-]+$',
                message='Никнейм может содержать только буквы, цифры, _ и -'
            )
        )
        self.fields['username'].help_text = None
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        forbidden = ['admin', 'administrator', 'root', 'moderator', 'support', 'wajos']
        if username.lower() in forbidden:
            raise ValidationError(f'Никнейм "{username}" зарезервирован')
        return username


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Никнейм',
        widget=forms.TextInput(attrs={
            'placeholder': 'Ваш никнейм',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Ваш пароль',
            'autocomplete': 'current-password',
        })
    )
    captcha = hCaptchaField(
        label='',
        error_messages={'required': 'Пожалуйста, подтвердите, что вы не робот'}
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = None
        self.error_messages['invalid_login'] = 'Неверный никнейм или пароль'


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'placeholder': 'Ваш никнейм',
                'autocomplete': 'username',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'email@example.com',
                'autocomplete': 'email',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = None

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        forbidden = ['admin', 'administrator', 'root', 'moderator', 'support', 'wajos']
        if username.lower() in forbidden:
            raise ValidationError(f'Никнейм "{username}" зарезервирован')
        qs = User.objects.exclude(pk=self.instance.pk).filter(username=username)
        if qs.exists():
            raise ValidationError('Этот никнейм уже занят')
        return username


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(
        label='Текущий пароль',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Введите текущий пароль',
            'autocomplete': 'current-password',
        })
    )
    new_password1 = forms.CharField(
        label='Новый пароль',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Минимум 8 символов',
            'autocomplete': 'new-password',
        })
    )
    new_password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Повторите новый пароль',
            'autocomplete': 'new-password',
        })
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old = self.cleaned_data.get('old_password', '')
        if self.user and not self.user.check_password(old):
            raise ValidationError('Неверный текущий пароль')
        return old

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password1', '')
        p2 = cleaned.get('new_password2', '')
        if p1 and p2 and p1 != p2:
            self.add_error('new_password2', 'Пароли не совпадают')
        if p1 and len(p1) < 8:
            self.add_error('new_password1', 'Пароль должен быть не менее 8 символов')
        return cleaned