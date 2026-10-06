from rest_framework.pagination import PageNumberPagination


class DemandePagination(PageNumberPagination):
    page_size = 20
    max_page_size = 20  # plafond imposé par l'énoncé : 20 demandes par page
    page_size_query_param = "page_size"
