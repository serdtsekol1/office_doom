from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        input_result = input("enter code: ")
        print('Тут має бути код)))', input_result)
