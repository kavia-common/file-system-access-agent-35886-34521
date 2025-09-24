from rest_framework import serializers


class PathQuerySerializer(serializers.Serializer):
    """Serializer for validating a filesystem path query parameter."""
    path = serializers.CharField(help_text="Absolute or project-relative path to a file or folder.")


class ListDirQuerySerializer(PathQuerySerializer):
    """Serializer for directory listing query parameters."""
    recursive = serializers.BooleanField(required=False, default=False, help_text="List recursively when true.")
    include_hidden = serializers.BooleanField(required=False, default=False, help_text="Include hidden files when true.")


class ReadFileQuerySerializer(PathQuerySerializer):
    """Serializer for reading files; supports range-like parameters."""
    offset = serializers.IntegerField(required=False, min_value=0, help_text="Byte offset to start reading from.")
    length = serializers.IntegerField(required=False, min_value=1, help_text="Maximum number of bytes to read.")
    encoding = serializers.ChoiceField(required=False, choices=["utf-8", "latin-1", "base64", "binary"], default="utf-8", help_text="Decoding method for response content.")


class WriteFileSerializer(serializers.Serializer):
    """Serializer for writing content to a file."""
    path = serializers.CharField(help_text="Target file path.")
    content = serializers.CharField(help_text="File content (text or base64 depending on encoding).")
    encoding = serializers.ChoiceField(required=False, choices=["utf-8", "latin-1", "base64", "binary"], default="utf-8", help_text="Encoding of provided content.")
    append = serializers.BooleanField(required=False, default=False, help_text="Append to file if true, otherwise overwrite.")


class MkdirSerializer(serializers.Serializer):
    """Serializer for directory creation."""
    path = serializers.CharField(help_text="Directory path to create.")
    parents = serializers.BooleanField(required=False, default=True, help_text="Create parent directories if needed.")
    exist_ok = serializers.BooleanField(required=False, default=True, help_text="Do not error if directory exists.")


class RemoveSerializer(serializers.Serializer):
    """Serializer for deletion of file or directory."""
    path = serializers.CharField(help_text="Path to remove.")
    recursive = serializers.BooleanField(required=False, default=False, help_text="Remove directories recursively if true.")
    force = serializers.BooleanField(required=False, default=False, help_text="Ignore missing files and permissions where possible.")


class MoveCopySerializer(serializers.Serializer):
    """Serializer for move/copy operations."""
    src = serializers.CharField(help_text="Source path.")
    dst = serializers.CharField(help_text="Destination path.")
    overwrite = serializers.BooleanField(required=False, default=False, help_text="Overwrite destination if exists.")


class RenameSerializer(serializers.Serializer):
    """Serializer for rename operation."""
    path = serializers.CharField(help_text="Existing path.")
    new_name = serializers.CharField(help_text="New base name for file or directory.")
    overwrite = serializers.BooleanField(required=False, default=False, help_text="Overwrite if new target exists.")


class UploadFileSerializer(serializers.Serializer):
    """Serializer for multipart upload."""
    path = serializers.CharField(help_text="Destination path for the uploaded file.")
    file = serializers.FileField(help_text="Uploaded file content.")


class SearchQuerySerializer(serializers.Serializer):
    """Serializer for simple file search."""
    path = serializers.CharField(help_text="Root directory to search.")
    pattern = serializers.CharField(help_text="Glob-like pattern, e.g., **/*.py")
    include_hidden = serializers.BooleanField(required=False, default=False, help_text="Include hidden files when true.")


class MCPToolCallSerializer(serializers.Serializer):
    """Serializer for MCP tool call."""
    tool_name = serializers.CharField(help_text="The MCP tool name to call, e.g., fs.read")
    arguments = serializers.DictField(child=serializers.JSONField(), help_text="Arguments for the tool call")


class MCPResponseSerializer(serializers.Serializer):
    """Serializer for MCP response envelope."""
    success = serializers.BooleanField()
    data = serializers.DictField(required=False)
    error = serializers.CharField(required=False)
