import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.contrib.auth import login as auth_login
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.db.models import Q
from .forms import PublisherForm
from .models import Article, Newsletter, Subscription
from .forms import ArticleSubmissionForm, UserRegistrationForm, NewsletterForm


# ACCESS CONTROL HELPERS
def is_editor(user):
    return user.is_authenticated and (
        user.groups.filter(name='Editor').exists() or
        user.is_superuser
    )


def is_journalist(user):
    """Strict Security Gate: Only Journalists and Superusers submit new article forms."""
    return user.is_authenticated and (
        user.groups.filter(name='Journalist').exists() or
        user.is_superuser
    )


# PUBLIC FEEDS & SIGN UP VIEWS
def homepage_view(request):
    global_articles = Article.objects.filter(approved=True).order_by('-created_at')
    global_newsletters = Newsletter.objects.all().order_by('-created_at')

    subscribed_articles = Article.objects.none()
    subscribed_newsletters = Newsletter.objects.none()
    user_author_subs = []
    user_pub_subs = []

    if request.user.is_authenticated:
        user_author_subs = list(
            Subscription.objects.filter(
                user=request.user,
                subscribed_author__isnull=False
            ).values_list('subscribed_author_id', flat=True)
        )

        user_pub_subs = list(
            Subscription.objects.filter(
                user=request.user,
                subscribed_publisher_id__isnull=False
            ).values_list('subscribed_publisher_id', flat=True)
        )

        if user_author_subs or user_pub_subs:
            subscribed_articles = (
                Article.objects.filter(approved=True).filter(
                    Q(author_id__in=user_author_subs) |
                    Q(publisher_id__in=user_pub_subs)
                ).order_by('-created_at').distinct()
            )

            subscribed_newsletters = (
                Newsletter.objects.filter(
                    author_id__in=user_author_subs
                ).order_by('-created_at')
            )

    combined_string_subs = (
        [f"author_{uid}" for uid in user_author_subs] +
        [f"pub_{pid}" for pid in user_pub_subs]
    )

    return render(request, 'articles/home.html', {
        'articles': global_articles,
        'newsletters': global_newsletters,
        'subscribed_articles': subscribed_articles,
        'subscribed_newsletters': subscribed_newsletters,
        'user_subscriptions': combined_string_subs
    })


def newsletter_detail_view(request, newsletter_id):
    newsletter = get_object_or_404(Newsletter, id=newsletter_id)
    attached_articles = newsletter.articles.filter(approved=True).order_by('-created_at')

    return render(request, 'articles/newsletter_detail.html', {
        'newsletter': newsletter,
        'articles': attached_articles
    })


@login_required
@require_POST
def toggle_subscription(request, publisher_id):
    target_type = request.POST.get('target_type')

    if target_type == 'author':
        subscription_queryset = Subscription.objects.filter(
            user=request.user,
            subscribed_author_id=publisher_id
        )
        if subscription_queryset.exists():
            subscription_queryset.delete()
        else:
            Subscription.objects.create(
                user=request.user,
                subscribed_author_id=publisher_id
            )
    else:
        subscription_queryset = Subscription.objects.filter(
            user=request.user,
            subscribed_publisher_id=publisher_id
        )
        if subscription_queryset.exists():
            subscription_queryset.delete()
        else:
            Subscription.objects.create(
                user=request.user,
                subscribed_publisher_id=publisher_id
            )

    return redirect(request.META.get('HTTP_REFERER', 'home'))


def register_user_view(request):
    """Handles new user signups with role assignment and authentication routing."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            auth_login(request, user)
            return redirect('home')
    else:
        form = UserRegistrationForm()

    return render(request, 'registration/register.html', {'form': form})


# JOURNALIST & SUBMISSION WORKSPACE
@login_required
@user_passes_test(is_journalist, login_url='home')
def submit_article_view(request):
    """Processes new news drafts, passing user context to the form filtering loops."""
    if request.method == 'POST':
        form = ArticleSubmissionForm(request.POST, user=request.user)
        form.user = request.user

        if form.is_valid():
            article = form.save(commit=False)

            if not article.publisher:
                article.author = request.user
            else:
                article.author = None

            article.approved = False

            try:
                article.full_clean()
                article.save()
                return redirect('home')
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = ArticleSubmissionForm(user=request.user)

    return render(request, 'articles/submit_article.html', {'form': form})

# EDITORIAL DASHBOARD WORKSPACE


@login_required
@user_passes_test(is_editor, login_url='home')
def editor_dashboard_view(request):
    """Protected Dashboard showing articles awaiting editor review."""

    if request.user.is_superuser:
        pending_articles = Article.objects.filter(approved=False).order_by('-created_at')

    else:

        user_publishers = request.user.publisher_journalists.all() | request.user.publisher_editors.all()
        user_publishers = user_publishers.distinct()

        pending_articles = Article.objects.filter(approved=False).filter(
            Q(publisher__in=user_publishers) | Q(publisher__isnull=True)
        ).distinct().order_by('-created_at')

    return render(request, 'articles/editor_dashboard.html', {'articles': pending_articles})


@login_required
@user_passes_test(is_editor, login_url='home')
def approve_article_action(request, article_id):
    """Approves an article draft."""
    article = get_object_or_404(Article, id=article_id)

    has_permission = request.user.is_superuser

    if article.publisher:
        is_journalist_staff = request.user in article.publisher.journalists.all()
        is_editor_staff = request.user in article.publisher.editors.all()
        if is_journalist_staff or is_editor_staff:
            has_permission = True

    else:
        if is_editor(request.user):
            has_permission = True

    if not has_permission:
        return redirect('home')

    article.approved = True
    article.save()
    return redirect('editor_dashboard')


# API SIMULATION
@csrf_exempt
def simulated_approved_api_endpoint(request):
    """Fake web endpoint to test sent notifications."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f"\n[API SIMULATION RECEIVER] Webhook Accepted for Article #{data.get('id')}: '{data.get('title')}'")
            return JsonResponse({'status': 'success', 'received_data': data}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid format'}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def edit_article_view(request, article_id):
    """Allows only network-authorized Editors and Superusers to edit articles."""
    article = get_object_or_404(Article, id=article_id)

    has_permission = False
    if request.user.is_superuser:
        has_permission = True
    elif article.publisher:
        if request.user in article.publisher.editors.all():
            has_permission = True
    else:
        if article.author == request.user:
            has_permission = True

    if not has_permission:
        raise PermissionDenied

    if request.method == 'POST':
        form = ArticleSubmissionForm(request.POST, instance=article, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = ArticleSubmissionForm(instance=article, user=request.user)

    return render(request, 'articles/edit_article.html', {'form': form, 'article': article})


def article_detail_view(request, article_id):
    article = get_object_or_404(Article, id=article_id)

    if not article.approved:
        if not request.user.is_authenticated:
            return redirect('home')

        is_superuser = request.user.is_superuser
        is_author = (article.author == request.user)
        is_staff = False

        if article.publisher:
            is_staff = (
                request.user in article.publisher.journalists.all()
                or request.user in article.publisher.editors.all()
            )

        if not (is_superuser or is_author or is_staff):
            return redirect('home')

    user_author_subs = []
    user_pub_subs = []
    if request.user.is_authenticated:
        user_author_subs = list(
            Subscription.objects.filter(
                user=request.user,
                subscribed_author__isnull=False
            ).values_list('subscribed_author_id', flat=True)
        )
        user_pub_subs = list(
            Subscription.objects.filter(
                user=request.user,
                subscribed_publisher_id__isnull=False
            ).values_list('subscribed_publisher_id', flat=True)
        )

    combined_string_subs = (
        [f"author_{uid}" for uid in user_author_subs] +
        [f"pub_{pid}" for pid in user_pub_subs]
    )

    return render(request, 'articles/article_detail.html', {
        'article': article,
        'user_subscriptions': combined_string_subs
    })


@login_required
def delete_article_view(request, article_id):
    """Allows only network-authorized Editors and Superusers to delete articles."""
    article = get_object_or_404(Article, id=article_id)

    has_permission = False
    if request.user.is_superuser:
        has_permission = True
    elif article.publisher:
        if request.user in article.publisher.editors.all():
            has_permission = True
    else:
        if article.author == request.user:
            has_permission = True

    if not has_permission:
        raise PermissionDenied

    if request.method == 'POST':
        article.delete()
        return redirect('home')

    return render(request, 'articles/delete_confirm.html', {'article': article})


@login_required
def write_newsletter(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='Journalist').exists()):
        raise PermissionDenied

    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            newsletter = form.save(commit=False)
            newsletter.author = request.user
            newsletter.save()
            form.save_m2m()
            return redirect('home')
    else:
        form = NewsletterForm()

    return render(request, 'articles/write_newsletter.html', {'form': form})


@login_required
def create_publisher_view(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    if request.method == 'POST':
        form = PublisherForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = PublisherForm()

    return render(request, 'articles/create_publisher.html', {'form': form})


@login_required
def edit_newsletter_view(request, newsletter_id):
    """Strictly restricts newsletter editing to Journalists or Superusers; blocks Editors."""
    newsletter = get_object_or_404(Newsletter, id=newsletter_id)

    is_journalist = hasattr(request.user, 'profile') and request.user.profile.role == 'journalist'

    if not (request.user.is_superuser or (request.user == newsletter.author and is_journalist)):
        raise PermissionDenied

    if request.method == 'POST':
        form = NewsletterForm(request.POST, instance=newsletter)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = NewsletterForm(instance=newsletter)

    return render(request, 'articles/write_newsletter.html', {'form': form, 'is_edit': True})


@login_required
def delete_newsletter_view(request, newsletter_id):
    """Strictly restricts newsletter deletion to Journalists or Superusers; blocks Editors."""
    newsletter = get_object_or_404(Newsletter, id=newsletter_id)

    is_journalist = hasattr(request.user, 'profile') and request.user.profile.role == 'journalist'

    if not (request.user.is_superuser or (request.user == newsletter.author and is_journalist)):
        raise PermissionDenied

    if request.method == 'POST':
        newsletter.delete()
        return redirect('home')

    return render(request, 'articles/delete_confirm.html', {'newsletter': newsletter})
