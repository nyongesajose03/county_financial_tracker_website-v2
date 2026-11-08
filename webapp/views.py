from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from .models import UserProfile, UserOpinion, Contact, FinancialData
from .forms import AccountDetailsForm, AccountProfileForm

# Create your views here.

ANNUAL_ALLOCATION_YEARS = (2024, 2025, 2026)
MONTHLY_ALLOCATION_WEIGHTS = (90, 95, 100, 105, 110, 110, 105, 100, 95, 90, 100, 100)


def _annual_allocation_rows(county, year_str):
    counties = UserProfile.COUNTY_CHOICES
    valid_counties = {county_name for county_name, _ in counties}

    if county != 'All' and county not in valid_counties:
        return []

    if year_str == 'All':
        years = ANNUAL_ALLOCATION_YEARS
    else:
        try:
            year = int(year_str)
        except ValueError:
            return []
        if year not in ANNUAL_ALLOCATION_YEARS:
            return []
        years = (year,)

    data = []
    for year in years:
        for county_index, (county_name, _) in enumerate(counties):
            if county != 'All' and county_name != county:
                continue

            amount = 8_000_000 + (
                (county_index * 37 + (year - 2024) * 113) % 701
            ) * 10_000
            data.append({
                'county': county_name,
                'year': year,
                'allocated_funds': amount,
                'allocatedFunds': amount,
            })

    return data


def _national_allocation_rows():
    totals = {year: 0 for year in ANNUAL_ALLOCATION_YEARS}
    for row in _annual_allocation_rows('All', 'All'):
        totals[row['year']] += row['allocated_funds']
    return [
        {'year': year, 'amount_display': f"{totals[year]:,}"}
        for year in ANNUAL_ALLOCATION_YEARS
    ]


def _monthly_allocation_rows(county, year_str, month):
    months = [month_name for month_name, _ in FinancialData.MONTH_CHOICES]
    if month != 'All' and month not in months:
        return []

    annual_data = _annual_allocation_rows(county, year_str)
    data = []
    total_weight = sum(MONTHLY_ALLOCATION_WEIGHTS)
    counties = UserProfile.COUNTY_CHOICES
    county_indexes = {
        county_name: index
        for index, (county_name, _) in enumerate(counties)
    }

    for annual_row in annual_data:
        allocations = [
            annual_row['allocated_funds'] * weight // total_weight
            for weight in MONTHLY_ALLOCATION_WEIGHTS
        ]
        remainder = annual_row['allocated_funds'] - sum(allocations)
        for month_index in range(remainder):
            allocations[month_index] += 1

        county_index = county_indexes[annual_row['county']]
        for month_index, month_name in enumerate(months):
            if month != 'All' and month_name != month:
                continue

            data.append({
                'county': annual_row['county'],
                'month': month_name,
                'year': annual_row['year'],
                'allocated_funds': allocations[month_index],
                'allocatedFunds': allocations[month_index],
                'revenue': (
                    1_000_000
                    + county_index * 50_000
                    + month_index * 125_000
                    + (annual_row['year'] - 2024) * 300_000
                ),
                'expenditure': (
                    600_000
                    + county_index * 25_000
                    + month_index * 80_000
                    + (annual_row['year'] - 2024) * 180_000
                ),
            })

    return data


def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        county = request.POST.get('county')
        role = request.POST.get('role')
        bio = request.POST.get('bio')
        
        # Check if passwords match
        if password1 != password2:
            messages.error(request, 'Passwords do not match!')
            return redirect('signup')
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return redirect('signup')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists!')
            return redirect('signup')
        
        # Create user
        user = User.objects.create_user(
            username=username, 
            email=email, 
            password=password1,
            first_name=first_name,
            last_name=last_name
        )
        
        # Create/Update user profile with additional information
        user_profile = user.profile
        user_profile.phone_number = phone_number
        user_profile.county = county
        user_profile.role = role
        user_profile.bio = bio
        user_profile.save()
        
        messages.success(request, 'Account created successfully! Please login.')
        return redirect('login')
    
    return render(request, 'signup.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            if request.POST.get('remember_device') == 'on':
                request.session.set_expiry(60 * 60 * 24 * 30)
            messages.success(request, f'Welcome, {username}!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password!')
            return redirect('login')
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully!')
    return redirect('login')

@login_required(login_url='login')
def home(request):
    return render(request, 'index.html')

@login_required(login_url='login')
def dashboard(request):
    return render(request, 'dashboard.html')


@login_required(login_url='login')
def project_tracker(request):
    return render(request, 'projecttracker.html', {
        'county_choices': UserProfile.COUNTY_CHOICES,
        'project_years': range(2024, 2033),
    })


def qrcode_page(request):
    return render(request, 'qrcode.html', {'site_url': settings.SITE_LAN_URL})

@login_required(login_url='login')
def budget_page(request):
    selected_county = request.GET.get('county', 'All')
    selected_year = request.GET.get('year', 'All')
    search_submitted = 'county' in request.GET or 'year' in request.GET
    budget_rows = (
        _annual_allocation_rows(selected_county, selected_year)
        if search_submitted
        else []
    )
    for row in budget_rows:
        row['amount_display'] = f"{row['allocated_funds']:,}"

    return render(request, 'budget.html', {
        'selected_county': selected_county,
        'selected_year': selected_year,
        'search_submitted': search_submitted,
        'budget_rows': budget_rows,
        'show_national_budget': (
            request.method == 'POST'
            and request.POST.get('show_national_budget') == '1'
        ),
        'national_budget_rows': (
            _national_allocation_rows()
            if (
                request.method == 'POST'
                and request.POST.get('show_national_budget') == '1'
            )
            else []
        ),
    })

@login_required(login_url='login')
def expenditure_page(request):
    return render(request, 'expenditure.html')

@login_required(login_url='login')
def revenue_page(request):
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    sample_amounts = {
        2024: [2500000, 2600000, 2750000, 2700000, 2900000, 3000000, 2950000, 3150000, 3250000, 3200000, 3400000, 3500000],
        2025: [3000000, 3100000, 3250000, 3200000, 3400000, 3500000, 3450000, 3650000, 3750000, 3700000, 3900000, 4000000],
        2026: [3500000, 3600000, 3750000, 3700000, 3900000, 4000000, 3950000, 4150000, 4250000],
    }
    chart_bottom = 410
    chart_top = 60
    minimum_amount = 2000000
    amount_range = 3000000
    charts = []

    for year, amounts in sample_amounts.items():
        last_x = 910
        x_spacing = (last_x - 140) / (len(amounts) - 1)
        points = []
        for index, amount in enumerate(amounts):
            x = round(140 + index * x_spacing)
            y = round(chart_bottom - (amount - minimum_amount) * (chart_bottom - chart_top) / amount_range)
            points.append({
                'x': x,
                'y': y,
                'month': month_names[index],
                'amount': f'{amount:,}',
            })

        charts.append({
            'year': year,
            'months': month_names[:len(amounts)],
            'points': points,
            'line_points': ' '.join(f"{point['x']},{point['y']}" for point in points),
            'period': 'Jan-Sep' if year == 2026 else 'Jan-Dec',
            'description': f"Monthly KES revenue from January through {month_names[len(amounts) - 1]} {year}.",
        })

    return render(request, 'revenue.html', {'charts': charts})

@login_required(login_url='login')
def finance(request):
    return render(request, 'financial-report.html')

@login_required(login_url='login')
def settings_page(request):
    return render(request, 'settings.html')

@login_required(login_url='login')
def profile(request):
    details_form = AccountDetailsForm(instance=request.user)
    profile_form = AccountProfileForm(instance=request.user.profile)
    password_form = PasswordChangeForm(request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            details_form = AccountDetailsForm(request.POST, instance=request.user)
            profile_form = AccountProfileForm(request.POST, instance=request.user.profile)
            if details_form.is_valid() and profile_form.is_valid():
                with transaction.atomic():
                    details_form.save()
                    profile_form.save()
                messages.success(request, 'Your account details have been updated.')
                return redirect('profile')

        elif action == 'change_password':
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password has been changed.')
                return redirect('profile')

        elif action == 'delete_account':
            if request.POST.get('confirm_delete') != 'DELETE':
                messages.error(request, 'Type DELETE to confirm permanent account deletion.')
            elif not request.user.check_password(request.POST.get('password', '')):
                messages.error(request, 'The password you entered is incorrect.')
            else:
                request.user.delete()
                logout(request)
                messages.success(request, 'Your account and associated records have been permanently deleted.')
                return redirect('login')

        else:
            messages.error(request, 'Invalid account action.')

    return render(request, 'profile.html', {
        'details_form': details_form,
        'profile_form': profile_form,
        'password_form': password_form,
    })

@login_required(login_url='login')
def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        county = request.POST.get('county')
        
        # Validation
        if not name or not email or not subject or not message:
            messages.error(request, 'Please fill in all required fields!')
            return redirect('contact')
        
        # Create contact message
        Contact.objects.create(
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message,
            county=county
        )
        
        messages.success(request, 'Your message has been sent successfully! We will get back to you soon.')
        return redirect('contact')
    
    return render(request, 'contact.html')

@login_required(login_url='login')
def finance_data(request):
    from django.http import JsonResponse
    from django.db.models import Sum

    county = request.GET.get('county', 'All')
    year_str = request.GET.get('year', '2025')
    month = request.GET.get('month', 'All')

    try:
        year = int(year_str)
    except ValueError:
        year = 2025

    queryset = FinancialData.objects.all()

    if county != 'All':
        queryset = queryset.filter(county=county)
    if month != 'All':
        queryset = queryset.filter(month=month)
    if year_str != 'All':
        queryset = queryset.filter(year=year)

    if request.GET.get('summary') == 'annual':
        data = list(
            queryset.values('county', 'year')
            .annotate(allocated_funds=Sum('allocated_funds'))
            .order_by('county', 'year')
        )
    else:
        data = list(queryset.values(
            'county',
            'month',
            'year',
            'allocated_funds',
            'revenue',
            'expenditure',
        ))
    for item in data:
        item['allocatedFunds'] = float(item['allocated_funds'])  # For JS formatting

    return JsonResponse({'data': data[:1000]})  # Limit for performance


@login_required(login_url='login')
def annual_allocation_data(request):
    from django.http import JsonResponse

    county = request.GET.get('county', 'All')
    year_str = request.GET.get('year', 'All')
    return JsonResponse({
        'data': _annual_allocation_rows(county, year_str),
    })


@login_required(login_url='login')
def monthly_allocation_data(request):
    from django.http import JsonResponse

    county = request.GET.get('county', 'All')
    year_str = request.GET.get('year', 'All')
    month = request.GET.get('month', 'All')
    return JsonResponse({
        'data': _monthly_allocation_rows(county, year_str, month),
    })


@login_required(login_url='login')
def financial_report_data(request):
    from django.http import JsonResponse

    county = request.GET.get('county', 'All')
    year_str = request.GET.get('year', 'All')
    month = request.GET.get('month', 'All')
    data = _monthly_allocation_rows(county, year_str, month)
    return JsonResponse({'data': data})


@login_required(login_url='login')
def about_feedback(request):
    return render(request, 'about-feedback.html')

@login_required(login_url='login')
def submit_opinion(request):
    """View for users to submit their opinions to the government"""
    if request.method == 'POST':
        opinion_type = request.POST.get('opinion_type')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        county = request.POST.get('county')
        department = request.POST.get('department')
        rating = request.POST.get('rating')
        is_public = request.POST.get('is_public') == 'on'
        
        # Validation
        if not subject or not message:
            messages.error(request, 'Subject and message are required!')
            return redirect('submit_opinion')
        
        # Create opinion
        opinion = UserOpinion.objects.create(
            user=request.user,
            opinion_type=opinion_type,
            subject=subject,
            message=message,
            county=county,
            department=department,
            rating=int(rating) if rating else None,
            is_public=is_public
        )
        
        messages.success(request, 'Your opinion has been submitted successfully! Thank you for your feedback.')
        return redirect('view_opinions')
    
    return render(request, 'submit_opinion.html')

@login_required(login_url='login')
def view_opinions(request):
    """View for users to see their submitted opinions"""
    user_opinions = UserOpinion.objects.filter(user=request.user)
    
    # Filter by status if provided
    status = request.GET.get('status')
    if status:
        user_opinions = user_opinions.filter(status=status)
    
    context = {
        'opinions': user_opinions,
        'status_choices': UserOpinion.STATUS_CHOICES,
    }
    
    return render(request, 'view_opinions.html', context)

@login_required(login_url='login')
def public_opinions(request):
    """View for all public opinions"""
    public_opinions = UserOpinion.objects.filter(is_public=True).select_related('user')
    
    # Filter by type if provided
    opinion_type = request.GET.get('type')
    if opinion_type:
        public_opinions = public_opinions.filter(opinion_type=opinion_type)
    
    context = {
        'opinions': public_opinions,
        'opinion_types': UserOpinion.OPINION_TYPE_CHOICES,
    }
    
    return render(request, 'public_opinions.html', context)