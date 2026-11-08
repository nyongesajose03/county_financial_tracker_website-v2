#!/usr/bin/env python3
"""
Seed script for FinancialData model.
Populates 5 counties x 12 months x 5 years (2024-2028) with sample data.
"""

import os
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
django.setup()

from webapp.models import FinancialData

def seed_data():
    counties = ['Nairobi', 'Nakuru', 'Kiambu', 'Kisumu', 'Mombasa']
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    years = range(2024, 2029)
    
    created = 0
    skipped = 0
    
    for county in counties:
        for year in years:
            for month in months:
                obj, new = FinancialData.objects.get_or_create(
                    county=county,
                    month=month,
                    year=year,
                    defaults={
                        'allocated_funds': Decimal(f'{3000000 + (year-2024)*500000 + (months.index(month)+1)*10000:.2f}'),
                        'revenue': Decimal(f'{2500000 + (year-2024)*400000 + (months.index(month)+1)*8000:.2f}'),
                        'expenditure': Decimal(f'{2800000 + (year-2024)*450000 + (months.index(month)+1)*9000:.2f}')
                    }
                )
                if new:
                    created += 1
                else:
                    skipped += 1
    
    print(f'Seeding complete: {created} new records created, {skipped} existing records skipped.')
    print(f'Total FinancialData: {FinancialData.objects.count()}')

if __name__ == '__main__':
    seed_data()

