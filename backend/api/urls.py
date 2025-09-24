from django.urls import path
from .views import (
    health,
    list_directory,
    read_file,
    write_file,
    make_directory,
    remove,
    copy,
    move,
    rename,
    search,
    mcp_tools,
    mcp_call,
)

urlpatterns = [
    path('health/', health, name='Health'),
    path('fs/list/', list_directory, name='list_directory'),
    path('fs/read/', read_file, name='read_file'),
    path('fs/write/', write_file, name='write_file'),
    path('fs/mkdir/', make_directory, name='make_directory'),
    path('fs/remove/', remove, name='remove'),
    path('fs/copy/', copy, name='copy'),
    path('fs/move/', move, name='move'),
    path('fs/rename/', rename, name='rename'),
    path('fs/search/', search, name='search'),
    path('mcp/tools/', mcp_tools, name='mcp_tools'),
    path('mcp/call/', mcp_call, name='mcp_call'),
]
