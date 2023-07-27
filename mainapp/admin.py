from django.contrib import admin
from django.utils.html import format_html

from mainapp.models import Product, Barcodes, Prices, Invoice, GoodGroups, DiadocInvoice, LinkedDocuments


class BarcodesInline(admin.TabularInline):
    model = Barcodes
    extra = 0


class PricesInline(admin.TabularInline):
    model = Prices
    extra = 0

class LinkedDocumentsInline(admin.TabularInline):
    model = LinkedDocuments
    extra = 0


@admin.register(GoodGroups)
class AdminGoodGroups(admin.ModelAdmin):
    list_display = ['id', 'group_id', 'name', 'pricingpercent', 'roundnumber', 'rule']
    list_editable = ['name', 'pricingpercent', 'roundnumber', 'rule']


@admin.register(DiadocInvoice)
class AdminProduct(admin.ModelAdmin):
#    search_fields = ['id', 'barcodes__code', 'name']
    list_display = ['id', 'diadoc_id', 'number']
@admin.register(Product)
class AdminProduct(admin.ModelAdmin):
    search_fields = ['id', 'barcodes__code', 'name']
    list_display = ['id', 'name', 'price', 'codes']
    list_editable = ['price', ]
    inlines = [BarcodesInline, PricesInline]

    def save_model(self, request, obj, form, change):
        try:
            print('save_model')
            # if not obj.show_in_categories.filter(id=obj.category_fk.id).exists():
            # obj.show_in_categories.set([c.id for c in list(obj.category_fk.get_ancestors(include_self=True))])
            # if len(form.cleaned_data['show_in_categories']) == 0 and obj.category_fk:
            #     form.cleaned_data['show_in_categories'] = [obj.category_fk]
        except Exception as ex:
            print(ex)
        super(AdminProduct, self).save_model(request, obj, form, change)


# @admin.register(Barcodes)
# class AdminBarcodes(admin.ModelAdmin):
#     pass
#
#
# @admin.register(Prices)
# class AdminPrices(admin.ModelAdmin):
#     pass

@admin.register(Invoice)
class AdminInvoices(admin.ModelAdmin):
    search_fields = ['id_dreem', 'supplier']
    list_display = [f.name for f in Invoice._meta.fields if f.name not in ['id', 'id_dreem']]
    list_editable = ['paid']
    list_filter = ['paid', 'supplier', 'issue_date','invoice_status']
    inlines = [LinkedDocumentsInline]
