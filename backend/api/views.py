from pathlib import Path
import os
import shutil

from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from .serializers import (
    ListDirQuerySerializer,
    ReadFileQuerySerializer,
    WriteFileSerializer,
    MkdirSerializer,
    RemoveSerializer,
    MoveCopySerializer,
    RenameSerializer,
    SearchQuerySerializer,
    MCPToolCallSerializer,
)
from .fs_utils import (
    resolve_safe_path,
    encode_content,
    decode_content,
    copy_or_move,
    ensure_parent_dir
)
from .mcp import MCPClient, MCPToolCall

# Default base directory for file operations: restrict to repository root by default
BASE_DIR = Path(settings.BASE_DIR).parent


# PUBLIC_INTERFACE
@api_view(['GET'])
def health(request):
    """Health check endpoint.
    Returns a simple message and a hint about the base directory restriction.
    """
    return Response({"message": "Server is up!", "base_dir": str(BASE_DIR)})


# PUBLIC_INTERFACE
@swagger_auto_schema(
    method='get',
    operation_description="List contents of a directory",
    query_serializer=ListDirQuerySerializer,
    responses={200: "List of directory contents"},
    tags=['filesystem']
)
@api_view(['GET'])
def list_directory(request):
    """List contents of a directory.

    Returns file and directory information for the specified path.
    Supports recursive listing and hidden file inclusion options.
    """
    serializer = ListDirQuerySerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        path = resolve_safe_path(BASE_DIR, serializer.validated_data['path'])
        if not path.exists():
            return Response(
                {"error": "Path does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )
        if not path.is_dir():
            return Response(
                {"error": "Path is not a directory"},
                status=status.HTTP_400_BAD_REQUEST
            )

        contents = []
        recursive = serializer.validated_data.get('recursive', False)
        include_hidden = serializer.validated_data.get('include_hidden', False)

        if recursive:
            for root, dirs, files in os.walk(path):
                root_path = Path(root)
                for name in dirs + files:
                    item_path = root_path / name
                    if not include_hidden and name.startswith('.'):
                        continue
                    rel_path = item_path.relative_to(path)
                    st = item_path.stat()
                    contents.append({
                        "name": name,
                        "path": str(rel_path),
                        "type": "directory" if item_path.is_dir() else "file",
                        "size": st.st_size if item_path.is_file() else None,
                        "modified": st.st_mtime
                    })
        else:
            for item in path.iterdir():
                if not include_hidden and item.name.startswith('.'):
                    continue
                st = item.stat()
                contents.append({
                    "name": item.name,
                    "path": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": st.st_size if item.is_file() else None,
                    "modified": st.st_mtime
                })

        return Response(contents)

    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to list directory: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# PUBLIC_INTERFACE
@swagger_auto_schema(
    method='get',
    operation_description="Read file contents",
    query_serializer=ReadFileQuerySerializer,
    responses={200: "File contents"},
    tags=['filesystem']
)
@api_view(['GET'])
def read_file(request):
    """Read contents of a file.

    Supports range-based reading and various encodings.
    """
    serializer = ReadFileQuerySerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        path = resolve_safe_path(BASE_DIR, serializer.validated_data['path'])
        if not path.exists():
            return Response(
                {"error": "File does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )
        if not path.is_file():
            return Response(
                {"error": "Path is not a file"},
                status=status.HTTP_400_BAD_REQUEST
            )

        offset = serializer.validated_data.get('offset', 0)
        length = serializer.validated_data.get('length', None)
        encoding = serializer.validated_data.get('encoding', 'utf-8')

        with open(path, 'rb') as f:
            if offset:
                f.seek(offset)
            data = f.read(length) if length else f.read()

        content = encode_content(data, encoding)
        return Response({
            "content": content,
            "encoding": encoding,
            "size": len(data)
        })

    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to read file: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# PUBLIC_INTERFACE
@swagger_auto_schema(
    method='post',
    operation_description="Write content to a file",
    request_body=WriteFileSerializer,
    responses={200: "Success response"},
    tags=['filesystem']
)
@api_view(['POST'])
def write_file(request):
    """Write content to a file.

    Supports various encodings and append mode.
    """
    serializer = WriteFileSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        path = resolve_safe_path(BASE_DIR, serializer.validated_data['path'])
        content = serializer.validated_data['content']
        encoding = serializer.validated_data.get('encoding', 'utf-8')
        append = serializer.validated_data.get('append', False)

        ensure_parent_dir(path)
        mode = 'ab' if append else 'wb'

        data = decode_content(content, encoding)
        with open(path, mode) as f:
            f.write(data)

        return Response({
            "message": "File written successfully",
            "size": len(data)
        })

    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to write file: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# PUBLIC_INTERFACE
@swagger_auto_schema(
    method='post',
    operation_description="Create a directory",
    request_body=MkdirSerializer,
    responses={200: "Success response"},
    tags=['filesystem']
)
@api_view(['POST'])
def make_directory(request):
    """Create a new directory.

    Supports creating parent directories and handling existing directories.
    """
    serializer = MkdirSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        path = resolve_safe_path(BASE_DIR, serializer.validated_data['path'])
        parents = serializer.validated_data.get('parents', True)
        exist_ok = serializer.validated_data.get('exist_ok', True)

        path.mkdir(parents=parents, exist_ok=exist_ok)
        return Response({"message": "Directory created successfully"})

    except FileExistsError:
        return Response(
            {"error": "Directory already exists"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to create directory: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# PUBLIC_INTERFACE
@swagger_auto_schema(
    method='post',
    operation_description="Remove a file or directory",
    request_body=RemoveSerializer,
    responses={200: "Success response"},
    tags=['filesystem']
)
@api_view(['POST'])
def remove(request):
    """Remove a file or directory.

    Supports recursive deletion and force options.
    """
    serializer = RemoveSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        path = resolve_safe_path(BASE_DIR, serializer.validated_data['path'])
        recursive = serializer.validated_data.get('recursive', False)
        force = serializer.validated_data.get('force', False)

        if not path.exists() and not force:
            return Response(
                {"error": "Path does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )

        if path.is_dir() and not path.is_symlink():
            if recursive:
                shutil.rmtree(path, ignore_errors=force)
            else:
                path.rmdir()
        else:
            path.unlink(missing_ok=force)

        return Response({"message": "Item removed successfully"})

    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to remove item: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# PUBLIC_INTERFACE
@swagger_auto_schema(
    method='post',
    operation_description="Copy a file or directory",
    request_body=MoveCopySerializer,
    responses={200: "Success response"},
    tags=['filesystem']
)
@api_view(['POST'])
def copy(request):
    """Copy a file or directory.

    Supports overwrite option.
    """
    serializer = MoveCopySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        src = resolve_safe_path(BASE_DIR, serializer.validated_data['src'])
        dst = resolve_safe_path(BASE_DIR, serializer.validated_data['dst'])
        overwrite = serializer.validated_data.get('overwrite', False)

        if not src.exists():
            return Response(
                {"error": "Source path does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )

        dst, overwritten = copy_or_move(src, dst, False, overwrite)
        return Response({
            "message": "Item copied successfully",
            "destination": str(dst.relative_to(BASE_DIR)),
            "overwritten": overwritten
        })

    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except FileExistsError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to copy item: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# PUBLIC_INTERFACE
@swagger_auto_schema(
    method='post',
    operation_description="Move a file or directory",
    request_body=MoveCopySerializer,
    responses={200: "Success response"},
    tags=['filesystem']
)
@api_view(['POST'])
def move(request):
    """Move a file or directory.

    Supports overwrite option.
    """
    serializer = MoveCopySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        src = resolve_safe_path(BASE_DIR, serializer.validated_data['src'])
        dst = resolve_safe_path(BASE_DIR, serializer.validated_data['dst'])
        overwrite = serializer.validated_data.get('overwrite', False)

        if not src.exists():
            return Response(
                {"error": "Source path does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )

        dst, overwritten = copy_or_move(src, dst, True, overwrite)
        return Response({
            "message": "Item moved successfully",
            "destination": str(dst.relative_to(BASE_DIR)),
            "overwritten": overwritten
        })

    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except FileExistsError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to move item: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# PUBLIC_INTERFACE
@swagger_auto_schema(
    method='post',
    operation_description="Rename a file or directory",
    request_body=RenameSerializer,
    responses={200: "Success response"},
    tags=['filesystem']
)
@api_view(['POST'])
def rename(request):
    """Rename a file or directory.

    Supports overwrite option.
    """
    serializer = RenameSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        path = resolve_safe_path(BASE_DIR, serializer.validated_data['path'])
        new_name = serializer.validated_data['new_name']
        overwrite = serializer.validated_data.get('overwrite', False)

        if not path.exists():
            return Response(
                {"error": "Path does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )

        new_path = path.parent / new_name
        new_path = resolve_safe_path(BASE_DIR, str(new_path))

        _, overwritten = copy_or_move(path, new_path, True, overwrite)
        return Response({
            "message": "Item renamed successfully",
            "new_path": str(new_path.relative_to(BASE_DIR)),
            "overwritten": overwritten
        })

    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except FileExistsError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to rename item: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# PUBLIC_INTERFACE
@swagger_auto_schema(
    method='get',
    operation_description="Search for files using glob pattern",
    query_serializer=SearchQuerySerializer,
    responses={200: "List of matching files"},
    tags=['filesystem']
)
@api_view(['GET'])
def search(request):
    """Search for files using glob pattern.

    Supports glob patterns and hidden file inclusion option.
    """
    serializer = SearchQuerySerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        root = resolve_safe_path(BASE_DIR, serializer.validated_data['path'])
        pattern = serializer.validated_data['pattern']
        include_hidden = serializer.validated_data.get('include_hidden', False)

        if not root.exists() or not root.is_dir():
            return Response(
                {"error": "Root path does not exist or is not a directory"},
                status=status.HTTP_404_NOT_FOUND
            )

        matches = []
        for path in root.glob(pattern):
            if not include_hidden and any(part.startswith('.') for part in path.parts):
                continue

            st = path.stat()
            matches.append({
                "name": path.name,
                "path": str(path.relative_to(root)),
                "type": "directory" if path.is_dir() else "file",
                "size": st.st_size if path.is_file() else None,
                "modified": st.st_mtime
            })

        return Response(matches)

    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to search: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# PUBLIC_INTERFACE
@swagger_auto_schema(
    method='get',
    operation_description="List available MCP tools from the MCP server",
    responses={200: "List of tools"},
    tags=['mcp']
)
@api_view(['GET'])
def mcp_tools(request):
    """List available MCP tools from the configured MCP server."""
    client = MCPClient()
    resp = client.list_tools()
    status_code = status.HTTP_200_OK if resp.success else status.HTTP_502_BAD_GATEWAY
    return Response({"success": resp.success, "data": resp.data, "error": resp.error}, status=status_code)


# PUBLIC_INTERFACE
@swagger_auto_schema(
    method='post',
    operation_description="Invoke an MCP tool by name with arguments",
    request_body=MCPToolCallSerializer,
    responses={200: "MCP tool execution result"},
    tags=['mcp']
)
@api_view(['POST'])
def mcp_call(request):
    """Invoke an MCP tool by name with arguments.

    This endpoint proxies a tool call to the MCP server. Implementation here is stubbed
    and should be replaced with a real MCP client when available.
    """
    serializer = MCPToolCallSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    client = MCPClient()
    call = MCPToolCall(
        tool_name=serializer.validated_data["tool_name"],
        arguments=serializer.validated_data.get("arguments", {}),
    )
    resp = client.call_tool(call)
    status_code = status.HTTP_200_OK if resp.success else status.HTTP_502_BAD_GATEWAY
    return Response({"success": resp.success, "data": resp.data, "error": resp.error}, status=status_code)
