from typing import Any, Dict, Union
from fastapi import HTTPException


def _generate_response(success: bool, message: str, status_code: int, data: Any = None) -> Dict[str, Any]:
    """
    Generate a standard API response.
    """
    response = {
        "success": success,
        "message": message,
        "status_code": status_code
    }
    if data is not None:
        response["data"] = data
    return response

def success_response(data: Any, message: str = "Request successful") -> Dict[str, Any]:
    """
    Generate a standard success response.
    """
    return _generate_response(success=True, message=message, status_code=200, data=data)

def error_response(detail: str, status_code: int, data: Any = None) -> Dict[str, Any]:
    """
    Generate a standard error response.
    """
    return _generate_response(success=False, message=detail, status_code=status_code, data=data)

def not_found_error(detail: str = "Resource not found") -> Dict[str, Any]:
    """
    Generate a 404 Not Found error response.
    """
    return error_response(detail=detail, status_code=404)

def permission_denied_error(detail: str = "Permission denied") -> Dict[str, Any]:
    """
    Raise a 403 Forbidden error.
    """
    return error_response(status_code=403, detail=detail)

def unauthorized_error(detail: str = "Invalid credentials") -> Dict[str, Any]:
    """
    Raise a 401 Unauthorized error.
    """
    return error_response(status_code=401, detail=detail)

def bad_request_error(data: Any = None, detail: str = "Bad request") -> Dict[str, Any]:
    """
    Generate a 400 Bad Request error response.
    """
    return error_response(detail=detail, status_code=400, data=data)



# def success_response(data: Any, message: str = "Request successful") -> Dict[str, Union[bool, str, dict]]:
#     """
#     Generate a standard success response.
#     """
#     return {
#         "success": True,
#         "message": message,
#         "data": data,
#         "status_code": 200
#     }

# def not_found_error(detail: str = "Resource not found") -> Dict[str, Any]:
#     """
#     Raise a 404 Not Found error.
#     """
#     # return HTTPException(status_code=404, detail=detail)
#     return {
#         'success': False,
#         'message': detail,
#         'status_code': 404
#     }

# def permission_denied_error(detail: str = "Permission denied") -> HTTPException:
#     """
#     Raise a 403 Forbidden error.
#     """
#     return HTTPException(status_code=403, detail=detail)

# def unauthorized_error(detail: str = "Invalid Credentials") -> HTTPException

# def bad_request_error(data: Any, detail: str = "Bad request") -> Dict[str, Any]:
#     """
#     Raise a 400 Bad Request error.
#     """
#     return {
#         'success': False,
#         'data': data,
#         'status_code': 400
#     }
