from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, RegexValidator


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = None
        self.error_messages['invalid_login'] = 'Неверный никнейм или пароль'
