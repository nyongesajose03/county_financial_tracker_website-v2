from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.html import escape

from .models import FinancialData, UserOpinion, UserProfile


class AccountManagementTests(TestCase):
    def setUp(self):
        self.password = 'InitialPassword!938'
        self.user = User.objects.create_user(
            username='account-holder',
            password=self.password,
            email='old@example.com',
            first_name='Old',
            last_name='Name',
        )
        self.profile = self.user.profile
        self.profile.phone_number = '0700000000'
        self.profile.county = 'Nairobi'
        self.profile.role = 'citizen'
        self.profile.save()
        self.client.force_login(self.user)

    def test_home_shows_county_and_year_fund_allocation_filters(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Anual Funds Allocation Overview')
        self.assertContains(response, 'Illustrative sample allocations (Ksh millions).')
        self.assertContains(response, 'Track Anual Funds')
        annual_table = response.content.decode().split(
            'id="annualReportTable">', 1
        )[1].split('</table>', 1)[0]
        self.assertIn('<th>County</th>', annual_table)
        self.assertIn('<th>Year</th>', annual_table)
        self.assertIn('<th>Amount</th>', annual_table)

        county_options = response.content.decode().split('id="countySelect">', 1)[1].split('</select>', 1)[0]
        self.assertEqual(county_options.count('<option '), 48)
        self.assertTrue(county_options.lstrip().startswith('<option value="All">All Counties</option>'))
        for county, _ in UserProfile.COUNTY_CHOICES:
            self.assertIn(f'<option value="{county}">{county}</option>', county_options)
        for year in range(2024, 2033):
            self.assertContains(response, f'<option value="{year}">{year}</option>')
        self.assertContains(response, '<option value="All">All Years</option>')

        monthly_county_options = response.content.decode().split(
            'id="monthlyCountySelect">', 1
        )[1].split('</select>', 1)[0]
        self.assertEqual(monthly_county_options.count('<option '), 48)
        self.assertTrue(
            monthly_county_options.lstrip().startswith(
                '<option value="All">All Counties</option>'
            )
        )
        for county, _ in UserProfile.COUNTY_CHOICES:
            self.assertIn(
                f'<option value="{county}">{county}</option>',
                monthly_county_options,
            )
        self.assertContains(response, 'Monthly Funds Allocation Overview')
        self.assertContains(
            response,
            'Illustrative monthly allocations sum to the annual allocation above.',
        )
        self.assertContains(response, 'Track Monthly Funds')
        self.assertContains(response, '<option value="All">All Months</option>')
        monthly_month_options = response.content.decode().split(
            'id="monthlyMonthSelect">', 1
        )[1].split('</select>', 1)[0]
        self.assertEqual(monthly_month_options.count('<option '), 13)
        for month in ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'):
            self.assertIn(f'<option value="{month}">{month}</option>', monthly_month_options)

    def test_project_tracker_page_shows_navigation_and_heading(self):
        response = self.client.get('/project-tracker/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'js/language.js')
        self.assertContains(response, 'County Government Project Tracker')
        self.assertContains(response, 'id="trackProjectsButton">Track Projects</button>')
        self.assertContains(response, 'id="projectTrackerTable">')
        for column in ('County', 'Year', 'Project', 'Name', 'Status', 'Expenses'):
            self.assertContains(response, f'<th>{column}</th>')
        self.assertContains(response, 'href="/">Home</a>')
        self.assertContains(response, 'href="/dashboard/">Dashboard</a>')
        self.assertContains(response, 'href="/finance/">Financial Reports</a>')
        self.assertContains(response, 'href="/project-tracker/">Project Tracker</a>')

    def test_budget_page_does_not_show_allocations_before_search(self):
        response = self.client.get('/budget/')

        self.assertEqual(response.status_code, 200)
        table = response.content.decode().split(
            'id="budgetRecordsTable">', 1
        )[1].split('</tbody>', 1)[0]
        table_body = table.split('<tbody>', 1)[1]
        self.assertIn('<th>County</th>', table)
        self.assertIn('<th>Year</th>', table)
        self.assertIn('<th>Amount</th>', table)
        self.assertEqual(table_body.count('<tr>'), 1)
        self.assertIn('click Track Funds', table_body)
        self.assertNotIn('<td>Baringo</td>', table_body)
        self.assertNotContains(response, 'id="nationalBudgetTable"')

    def test_budget_page_lists_allocations_after_search(self):
        filtered_response = self.client.get('/budget/', {
            'county': 'Nairobi',
            'year': '2025',
        })
        filtered_table = filtered_response.content.decode().split(
            'id="budgetRecordsTable">', 1
        )[1].split('</tbody>', 1)[0]
        filtered_table_body = filtered_table.split('<tbody>', 1)[1]
        self.assertIn('<td>Nairobi</td>', filtered_table)
        self.assertIn('<td>2025</td>', filtered_table)
        self.assertEqual(filtered_table_body.count('<tr>'), 1)
        self.assertIn('Ksh ', filtered_table_body)

    def test_national_budget_is_shown_on_request_and_sums_counties_by_year(self):
        initial_response = self.client.get('/budget/')
        self.assertNotContains(initial_response, 'id="nationalBudgetTable"')
        query_response = self.client.get('/budget/', {
            'show_national_budget': '1',
        })
        self.assertNotContains(query_response, 'id="nationalBudgetTable"')

        response = self.client.post('/budget/', {'show_national_budget': '1'})

        self.assertEqual(response.status_code, 200)
        national_table = response.content.decode().split(
            'id="nationalBudgetTable">', 1
        )[1].split('</tbody>', 1)[0]
        national_rows = national_table.split('<tbody>', 1)[1].split('<tr>')[1:]
        county_rows = self.client.get('/finance/annual-allocation-data/', {
            'county': 'All',
            'year': 'All',
        }).json()['data']
        expected_totals = {}
        for row in county_rows:
            expected_totals[row['year']] = (
                expected_totals.get(row['year'], 0) + row['allocatedFunds']
            )
        self.assertEqual(len(national_rows), 3)
        for year, amount in expected_totals.items():
            self.assertIn(f'<td>{year}</td>', national_table)
            self.assertIn(f'<td>Ksh {amount:,}</td>', national_table)

    def test_budget_page_shows_no_data_for_unsupported_year(self):
        response = self.client.get('/budget/', {
            'county': 'Nairobi',
            'year': '2027',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No data found.')
        table = response.content.decode().split(
            'id="budgetRecordsTable">', 1
        )[1].split('</tbody>', 1)[0]
        table_body = table.split('<tbody>', 1)[1]
        self.assertEqual(table_body.count('<tr>'), 1)

    def test_project_tracker_link_appears_in_other_navigation_bars(self):
        page_paths = (
            '/',
            '/dashboard/',
            '/finance/',
            '/about/',
            '/contact/',
            '/opinion/public/',
            '/opinion/my-opinions/',
            '/opinion/submit/',
        )
        for page_path in page_paths:
            with self.subTest(page_path=page_path):
                response = self.client.get(page_path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    'href="/project-tracker/">Project Tracker</a>',
                )

    def test_project_tracker_shows_county_year_and_status_filters(self):
        response = self.client.get('/project-tracker/')

        self.assertEqual(response.status_code, 200)
        county_options = response.content.decode().split(
            'id="projectCountySelect">', 1
        )[1].split('</select>', 1)[0]
        self.assertTrue(
            county_options.lstrip().startswith(
                '<option value="All">All Counties</option>'
            )
        )
        for county, _ in UserProfile.COUNTY_CHOICES:
            escaped_county = escape(county)
            self.assertIn(
                f'<option value="{escaped_county}">{escaped_county}</option>',
                county_options,
            )

        year_options = response.content.decode().split(
            'id="projectYearSelect">', 1
        )[1].split('</select>', 1)[0]
        self.assertTrue(
            year_options.lstrip().startswith(
                '<option value="All">All Years</option>'
            )
        )
        for year in range(2024, 2033):
            self.assertIn(f'<option value="{year}">{year}</option>', year_options)

        status_options = response.content.decode().split(
            'id="projectStatusSelect">', 1
        )[1].split('</select>', 1)[0]
        self.assertTrue(
            status_options.lstrip().startswith(
                '<option value="All">All Status</option>'
            )
        )
        for status in ('Ongoing', 'Completed', 'Pending', 'Delayed'):
            self.assertIn(f'<option value="{status}">{status}</option>', status_options)

    def test_annual_allocation_data_is_fixed_for_every_county_and_supported_year(self):
        response = self.client.get('/finance/annual-allocation-data/', {
            'county': 'All',
            'year': 'All',
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(
            len(data),
            len(UserProfile.COUNTY_CHOICES) * 3,
        )
        self.assertEqual(
            {(row['county'], row['year']) for row in data},
            {
                (county, year)
                for county, _ in UserProfile.COUNTY_CHOICES
                for year in (2024, 2025, 2026)
            },
        )
        self.assertTrue(all(
            8_000_000 <= row['allocatedFunds'] <= 15_000_000
            for row in data
        ))

        repeated_response = self.client.get('/finance/annual-allocation-data/', {
            'county': 'All',
            'year': 'All',
        })
        self.assertEqual(repeated_response.json()['data'], data)

        filtered_response = self.client.get('/finance/annual-allocation-data/', {
            'county': 'Nairobi',
            'year': '2025',
        })
        self.assertEqual(filtered_response.json()['data'][0]['county'], 'Nairobi')
        self.assertEqual(filtered_response.json()['data'][0]['year'], 2025)

    def test_annual_allocation_data_returns_no_data_for_unsupported_years(self):
        for year in ('2023', '2027', 'not-a-year'):
            with self.subTest(year=year):
                response = self.client.get('/finance/annual-allocation-data/', {
                    'county': 'All',
                    'year': year,
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['data'], [])

    def test_monthly_allocation_data_sums_to_annual_allocation(self):
        response = self.client.get('/finance/monthly-allocation-data/', {
            'county': 'All',
            'year': 'All',
            'month': 'All',
        })

        self.assertEqual(response.status_code, 200)
        monthly_data = response.json()['data']
        self.assertEqual(
            len(monthly_data),
            len(UserProfile.COUNTY_CHOICES) * 3 * 12,
        )

        annual_data = self.client.get('/finance/annual-allocation-data/', {
            'county': 'All',
            'year': 'All',
        }).json()['data']
        monthly_totals = {}
        months_by_county_year = {}
        monthly_amounts = {}
        for row in monthly_data:
            key = (row['county'], row['year'])
            monthly_totals[key] = monthly_totals.get(key, 0) + row['allocatedFunds']
            months_by_county_year.setdefault(key, set()).add(row['month'])
            monthly_amounts.setdefault(key, []).append(row['allocatedFunds'])

        annual_totals = {
            (row['county'], row['year']): row['allocatedFunds']
            for row in annual_data
        }
        self.assertEqual(monthly_totals, annual_totals)
        self.assertTrue(all(len(months) == 12 for months in months_by_county_year.values()))
        self.assertTrue(all(
            len(set(amounts)) > 1
            for amounts in monthly_amounts.values()
        ))
        self.assertTrue(all(
            len(set(amounts)) < len(amounts)
            for amounts in monthly_amounts.values()
        ))

        repeated_response = self.client.get('/finance/monthly-allocation-data/', {
            'county': 'All',
            'year': 'All',
            'month': 'All',
        })
        self.assertEqual(repeated_response.json()['data'], monthly_data)

        single_month_response = self.client.get('/finance/monthly-allocation-data/', {
            'county': 'Nairobi',
            'year': '2025',
            'month': 'Feb',
        })
        self.assertEqual(single_month_response.json()['data'][0]['county'], 'Nairobi')
        self.assertEqual(single_month_response.json()['data'][0]['year'], 2025)
        self.assertEqual(single_month_response.json()['data'][0]['month'], 'Feb')

    def test_monthly_allocation_data_returns_no_data_for_unsupported_filters(self):
        unsupported_filters = (
            {'county': 'All', 'year': '2027', 'month': 'All'},
            {'county': 'All', 'year': '2024', 'month': 'NotAMonth'},
            {'county': 'NotACounty', 'year': '2024', 'month': 'All'},
        )
        for filters in unsupported_filters:
            with self.subTest(filters=filters):
                response = self.client.get('/finance/monthly-allocation-data/', filters)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['data'], [])

    def test_finance_data_all_years_returns_records_across_years(self):
        FinancialData.objects.create(
            county='Nairobi',
            month='Jan',
            year=2024,
            allocated_funds=Decimal('100.00'),
            revenue=Decimal('80.00'),
            expenditure=Decimal('70.00'),
        )
        FinancialData.objects.create(
            county='Nairobi',
            month='Feb',
            year=2025,
            allocated_funds=Decimal('200.00'),
        )
        FinancialData.objects.create(
            county='Kiambu',
            month='Jan',
            year=2024,
            allocated_funds=Decimal('300.00'),
        )

        response = self.client.get('/finance/data/', {
            'county': 'Nairobi',
            'year': 'All',
            'month': 'All',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual({row['year'] for row in response.json()['data']}, {2024, 2025})
        first_record = next(
            row for row in response.json()['data']
            if row['county'] == 'Nairobi' and row['year'] == 2024
        )
        self.assertEqual(first_record['revenue'], '80.00')
        self.assertEqual(first_record['expenditure'], '70.00')
        self.assertEqual(first_record['allocatedFunds'], 100.0)

        response = self.client.get('/finance/data/', {
            'county': 'Nairobi',
            'year': 'All',
            'month': 'Feb',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [(row['month'], row['year']) for row in response.json()['data']],
            [('Feb', 2025)],
        )

    def test_financial_report_shows_frng_column_and_note(self):
        response = self.client.get('/finance/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<th>FRNG</th>')
        self.assertContains(response, '<th>Year</th>')
        self.assertContains(response, '<option value="2024">2024</option>')
        self.assertContains(
            response,
            'Note: FRNG is Fund Received from National Goverment',
        )
        self.assertContains(response, 'id="generateReport"')

    def test_financial_report_data_covers_supported_years_and_matches_monthly_frng(self):
        response = self.client.get('/finance/report-data/', {
            'county': 'All',
            'year': 'All',
            'month': 'All',
        })

        self.assertEqual(response.status_code, 200)
        report_data = response.json()['data']
        expected_row_count = len(UserProfile.COUNTY_CHOICES) * 3 * 12
        self.assertEqual(len(report_data), expected_row_count)
        self.assertEqual(
            {row['year'] for row in report_data},
            {2024, 2025, 2026},
        )
        self.assertTrue(all(row['revenue'] > 0 for row in report_data))
        self.assertTrue(all(row['expenditure'] > 0 for row in report_data))

        monthly_data = self.client.get('/finance/monthly-allocation-data/', {
            'county': 'All',
            'year': 'All',
            'month': 'All',
        }).json()['data']
        self.assertEqual(
            [
                (row['county'], row['month'], row['year'], row['allocatedFunds'])
                for row in report_data
            ],
            [
                (row['county'], row['month'], row['year'], row['allocatedFunds'])
                for row in monthly_data
            ],
        )
        self.assertGreater(
            len({row['revenue'] for row in report_data}),
            1,
        )
        self.assertGreater(
            len({row['expenditure'] for row in report_data}),
            1,
        )

    def test_financial_report_data_returns_no_data_for_unsupported_filters(self):
        filters = (
            {'county': 'All', 'year': '2027', 'month': 'All'},
            {'county': 'Nairobi', 'year': '2024', 'month': 'NotAMonth'},
            {'county': 'Unknown', 'year': '2024', 'month': 'All'},
        )
        for filter_params in filters:
            with self.subTest(filters=filter_params):
                response = self.client.get('/finance/report-data/', filter_params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['data'], [])

    def test_finance_data_annual_summary_groups_monthly_allocations_by_county_and_year(self):
        FinancialData.objects.create(
            county='Nairobi',
            month='Jan',
            year=2024,
            allocated_funds=Decimal('100.00'),
        )
        FinancialData.objects.create(
            county='Nairobi',
            month='Feb',
            year=2024,
            allocated_funds=Decimal('200.00'),
        )

        response = self.client.get('/finance/data/', {
            'county': 'Nairobi',
            'year': 'All',
            'month': 'All',
            'summary': 'annual',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data'], [{
            'county': 'Nairobi',
            'year': 2024,
            'allocated_funds': '300',
            'allocatedFunds': 300.0,
        }])

    def test_profile_requires_authentication_and_shows_account_fields(self):
        self.client.logout()
        response = self.client.get('/profile/')
        self.assertRedirects(response, '/login/?next=/profile/')

        self.client.force_login(self.user)
        response = self.client.get('/profile/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Back to settings"')
        self.assertContains(response, 'href="/settings/"')
        for field in ('first_name', 'last_name', 'username', 'email', 'phone_number', 'county', 'role'):
            self.assertContains(response, f'name="{field}"')

    def test_settings_page_exposes_persistent_site_language_selection(self):
        response = self.client.get('/settings/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="language-setting"')
        self.assertContains(response, 'value="sw"')
        self.assertContains(response, 'js/language.js')

    def test_login_can_remember_a_device_for_thirty_days_after_password_authentication(self):
        self.client.logout()
        response = self.client.post('/login/', {
            'username': self.user.username,
            'password': self.password,
            'remember_device': 'on',
        })

        self.assertRedirects(response, '/')
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertGreaterEqual(
            self.client.session.get_expiry_age(),
            60 * 60 * 24 * 29,
        )

    def test_qr_code_page_is_public_and_points_to_the_local_site(self):
        self.client.logout()
        response = self.client.get('/qrcode/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'images/site-access-qr.png')
        self.assertContains(response, 'http://10.241.151.21:8000/')
        self.assertContains(response, 'aria-label="Back to settings"')
        self.assertContains(response, 'href="/settings/"')

    def test_dashboard_shows_budget_chart_for_2024_to_2026(self):
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'National Government Budget (2024-2032)')
        self.assertContains(response, 'Budget amounts in KSh millions')
        self.assertContains(response, 'points="100,230 206,110 313,170"')
        self.assertContains(response, 'National Government Revenue (2024-2032)')
        self.assertContains(response, 'Revenue amounts in KSh millions')
        self.assertContains(response, 'points="100,122 206,50"')
        self.assertContains(response, 'National Government Expenditure (2024-2032)')
        self.assertContains(response, 'Expenditure amounts in KSh millions')
        self.assertContains(response, 'points="100,122 206,230"')
        for year in range(2024, 2033):
            self.assertContains(response, str(year))

        self.client.logout()
        response = self.client.get('/dashboard/')
        self.assertRedirects(response, '/login/?next=/dashboard/')

    def test_expenditure_page_shows_monthly_charts_and_marks_sample_data(self):
        response = self.client.get('/expenditure/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'National Government Expenditure (2024-2032)')
        self.assertContains(response, 'Expenditure Year 2024')
        self.assertContains(response, 'Expenditure Year 2025')
        self.assertContains(response, 'Expenditure Year 2026')
        self.assertContains(response, 'Illustrative sample data')
        self.assertContains(response, 'Amount in KES by month (Jan-Sep)')
        for month in ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'):
            self.assertContains(response, month)

        self.client.logout()
        response = self.client.get('/expenditure/')
        self.assertRedirects(response, '/login/?next=/expenditure/')

    def test_revenue_page_shows_monthly_charts_and_marks_sample_data(self):
        response = self.client.get('/revenue/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'National Government Revenue (2024-2032)')
        self.assertContains(response, 'Revenue Year 2024')
        self.assertContains(response, 'Revenue Year 2025')
        self.assertContains(response, 'Revenue Year 2026')
        self.assertContains(response, 'Illustrative sample data')
        self.assertContains(response, 'Amount in KES by month (Jan-Sep)')
        self.assertContains(response, 'KES 2,500,000')
        self.assertContains(response, 'KES 4,250,000')
        self.assertEqual(response.content.count(b'<svg '), 3)
        self.assertContains(response, '>Dec</text>', count=2)
        self.assertContains(response, '>Sep</text>', count=3)

        self.client.logout()
        response = self.client.get('/revenue/')
        self.assertRedirects(response, '/login/?next=/revenue/')

    def test_user_can_update_personal_and_profile_details(self):
        response = self.client.post('/profile/', {
            'action': 'update_profile',
            'first_name': 'New',
            'last_name': 'Person',
            'username': 'new-username',
            'email': 'new@example.com',
            'phone_number': '0712345678',
            'county': 'Kiambu',
            'role': 'government official',
        })

        self.assertRedirects(response, '/profile/')
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'New')
        self.assertEqual(self.user.last_name, 'Person')
        self.assertEqual(self.user.username, 'new-username')
        self.assertEqual(self.user.email, 'new@example.com')
        self.assertEqual(self.user.profile.phone_number, '0712345678')
        self.assertEqual(self.user.profile.county, 'Kiambu')
        self.assertEqual(self.user.profile.role, 'government official')

    def test_user_can_change_password_without_being_logged_out(self):
        new_password = 'BrandNewPassword!835'
        response = self.client.post('/profile/', {
            'action': 'change_password',
            'old_password': self.password,
            'new_password1': new_password,
            'new_password2': new_password,
        })

        self.assertRedirects(response, '/profile/')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        self.assertEqual(self.client.get('/profile/').status_code, 200)

    def test_user_can_logout_and_protected_pages_require_login(self):
        response = self.client.get('/logout/')
        self.assertRedirects(response, '/login/')
        response = self.client.get('/')
        self.assertRedirects(response, '/login/?next=/')

    def test_account_deletion_removes_user_and_cascaded_records(self):
        opinion = UserOpinion.objects.create(
            user=self.user,
            subject='My opinion',
            message='A message',
        )
        profile_id = self.user.profile.pk

        response = self.client.post('/profile/', {
            'action': 'delete_account',
            'password': self.password,
            'confirm_delete': 'DELETE',
        })

        self.assertRedirects(response, '/login/')
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(UserProfile.objects.filter(pk=profile_id).exists())
        self.assertFalse(UserOpinion.objects.filter(pk=opinion.pk).exists())
        response = self.client.get('/')
        self.assertRedirects(response, '/login/?next=/')

    def test_account_deletion_requires_password_and_explicit_confirmation(self):
        response = self.client.post('/profile/', {
            'action': 'delete_account',
            'password': 'incorrect-password',
            'confirm_delete': 'DELETE',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertEqual(self.client.get('/profile/').status_code, 200)
