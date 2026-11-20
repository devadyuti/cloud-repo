---
name: "office-files"
displayName: "Office & File Management"
description: "Read and edit Excel workbooks, Word documents, and access OneDrive files"
keywords: ["excel", "word", "office", "spreadsheet", "document", "onedrive", "workbook", "file"]
author: "demo-author"
---

# Overview

Office document management — read/write Excel workbooks, read Word documents, and access files on OneDrive.

## Available MCP Servers

### gandalf-mcp-server
Microsoft Office document manipulation — Excel workbooks and Word documents.

**Tools:**
- `open_excel_workbook` - Open an Excel workbook
- `list_excel_workbooks` - List available workbooks
- `get_excel_workbook_metadata` - Get workbook metadata
- `read_excel_data` - Read data from Excel sheets
- `run_excel_custom_script` - Run custom scripts on workbooks
- `close_excel_workbook` - Close a workbook
- `read_word_text` - Read text from Word documents
- `close_word_document` - Close a Word document
- `create_excel_worksheet` - Create a new worksheet
- `copy_excel_range` - Copy a range of cells

### onedrive
OneDrive file system access — read files from your Amazon OneDrive.

**Tools:**
- `read_file` - Read a text file from OneDrive
- `read_multiple_files` - Read multiple files
- `write_file` - Write content to a file
- `list_directory` - List directory contents
- `search_files` - Search for files
- `create_directory` - Create a directory
- `move_file` - Move/rename a file

## Best Practices

- Always close workbooks/documents when done to free resources
- Use `read_excel_data` with specific ranges rather than reading entire sheets
- OneDrive path root is `/Users/your-user/OneDrive - example`
