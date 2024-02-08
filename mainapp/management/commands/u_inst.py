from django.core.management import BaseCommand
import json

from mainapp.models import Invoice


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Open the file
        with open('db_dump.json', 'r') as f:
            # Load the JSON data
            data = json.load(f)
            i = 0
            for obj in data:
                i = i + 1
                print(i)
                print(obj['fields'])
                Invoice.objects.create(
                    id_dreem=obj['fields']['id_dreem'],
                    supplier=obj['fields']['supplier'],
                    number=obj['fields']['number'],
                    sum=obj['fields']['sum'],
                    paid=obj['fields']['paid'],
                    invoicetype=obj['fields']['invoicetype'],
                    issue_date=obj['fields']['issue_date'],
                                       )