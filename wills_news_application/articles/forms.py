from django import forms
from django.contrib.auth.models import User
from .models import Article, Publisher, UserProfile, Newsletter


class ArticleSubmissionForm(forms.ModelForm):
    """Form used by journalists and editors to submit news content."""

    class Meta:
        model = Article
        fields = ['title', 'content', 'publisher']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter article headline...',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Write your news content here...',
                'rows': 10,
            }),
            'publisher': forms.Select(attrs={
                'class': 'form-select',
            }),
        }

    def __init__(self, *args, **kwargs):
        """Initialises user context and filters choices."""
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            if self.user.is_superuser:
                self.fields['publisher'].queryset = Publisher.objects.all()
            else:
                q_set = self.user.publisher_journalists.all()
                self.fields['publisher'].queryset = q_set

        self.fields['publisher'].required = False
        self.fields['publisher'].empty_label = (
            "Publish as Independent Journalist"
        )

    def clean_publisher(self):
        """Verifies writer authorization metrics."""
        publisher = self.cleaned_data.get('publisher')
        if publisher and self.user and not self.user.is_superuser:
            if self.user not in publisher.journalists.all():
                raise forms.ValidationError(
                    "Access Denied: Unauthorized publisher posting."
                )
        return publisher

    def clean(self):
        """Maintains split multi-tenant profile mappings."""
        cleaned_data = super().clean()
        publisher = cleaned_data.get('publisher')

        if publisher:
            self.instance.publisher = publisher
            self.instance.author = None
        else:
            if self.user:
                self.instance.author = self.user
            elif not self.instance.author:
                first_user = User.objects.first()
                if first_user:
                    self.instance.author = first_user
            self.instance.publisher = None

        return cleaned_data


class UserRegistrationForm(forms.ModelForm):
    """Form used by new readers and staff members to sign up."""

    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-input',
        'placeholder': 'Create a secure password...'
    }))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-input',
        'placeholder': 'Repeat your password...'
    }), label="Confirm Password")

    role = forms.ChoiceField(
        choices=[
            ('reader', 'Reader'),
            ('journalist', 'Journalist'),
            ('editor', 'Editor'),
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-input'})
    )

    publisher = forms.ModelChoiceField(
        queryset=Publisher.objects.all(),
        required=False,
        empty_label="Select your publisher network...",
        widget=forms.Select(attrs={'class': 'form-input'})
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(
                attrs={'class': 'form-input', 'placeholder': 'Username...'}
            ),
            'email': forms.EmailInput(
                attrs={'class': 'form-input', 'placeholder': 'Email...'}
            ),
        }

    def clean_username(self):
        """Checks duplicate system username constraints."""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean(self):
        """Validates matching password inputs."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        """Saves user data and builds role profiles."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            role_choice = self.cleaned_data['role']
            profile.role = role_choice
            profile.save()

            publisher = self.cleaned_data.get('publisher')
            if publisher and role_choice in ['journalist', 'editor']:
                if role_choice == 'journalist':
                    publisher.journalists.add(user)
                elif role_choice == 'editor':
                    publisher.editors.add(user)

        return user


class NewsletterForm(forms.ModelForm):
    """Form used by journalists to create and edit curated article digests."""

    articles = forms.ModelMultipleChoiceField(
        queryset=Article.objects.filter(approved=True),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'style': 'margin-right: 0.5rem;'
        })
    )

    class Meta:
        model = Newsletter
        fields = ['title', 'description', 'articles']
        widgets = {
            'title': forms.TextInput(attrs={
                'style': (
                    'width: 100%; padding: 0.5rem; '
                    'border: 1px solid #e2e8f0; border-radius: 8px; '
                    'margin-bottom: 1rem; font-family: inherit;'
                )
            }),
            'description': forms.Textarea(attrs={
                'style': (
                    'width: 100%; padding: 0.5rem; '
                    'border: 1px solid #e2e8f0; border-radius: 8px; '
                    'margin-bottom: 1rem; font-family: inherit; '
                    'min-height: 120px;'
                )
            }),
        }


class PublisherForm(forms.ModelForm):
    """Form used by superusers to register new corporate media networks."""

    class Meta:
        model = Publisher
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'style': (
                    'width: 100%; padding: 0.5rem; '
                    'border: 1px solid #e2e8f0; border-radius: 8px; '
                    'margin-bottom: 1rem; font-family: inherit;'
                )
            }),
        }
