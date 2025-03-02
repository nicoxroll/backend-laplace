from functools import wraps
from flask import request, jsonify
from typing import Dict, Any, Callable, List, Union

class RequestValidationError(Exception):
    """Exception raised for request validation errors."""
    def __init__(self, message: str, errors: List[Dict[str, Any]] = None):
        self.message = message
        self.errors = errors or []
        super().__init__(self.message)

def validate_schema(schema):
    """
    Decorator to validate request data against a schema.
    
    Args:
        schema: A schema object with a validate method (e.g., marshmallow Schema)
    
    Returns:
        Decorator function that validates request data
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.is_json:
                data = request.get_json()
            elif request.form:
                data = request.form.to_dict()
            else:
                data = {}
            
            errors = schema().validate(data)
            if errors:
                return jsonify({
                    'error': 'Validation Error',
                    'message': 'Invalid request data',
                    'details': errors
                }), 400
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_request_params(params: Dict[str, Any]):
    """
    Decorator to validate request parameters.
    
    Args:
        params: Dictionary mapping parameter names to their expected types/validators
    
    Returns:
        Decorator function that validates request parameters
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            errors = {}
            for param_name, validator in params.items():
                value = request.args.get(param_name)
                if value is None and validator.get('required', False):
                    errors[param_name] = f"Parameter '{param_name}' is required"
                    continue
                    
                if value is not None:
                    try:
                        # Type validation
                        param_type = validator.get('type')
                        if param_type:
                            if param_type == int:
                                value = int(value)
                            elif param_type == float:
                                value = float(value)
                            elif param_type == bool:
                                value = value.lower() in ('true', '1', 'yes')
                                
                        # Custom validation
                        if 'validator' in validator and callable(validator['validator']):
                            if not validator['validator'](value):
                                errors[param_name] = f"Invalid value for parameter '{param_name}'"
                                
                    except (ValueError, TypeError):
                        errors[param_name] = f"Invalid type for parameter '{param_name}'"
            
            if errors:
                return jsonify({
                    'error': 'Validation Error',
                    'message': 'Invalid request parameters',
                    'details': errors
                }), 400
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def handle_validation_errors(app):
    """
    Register error handlers for validation errors.
    
    Args:
        app: Flask application instance
    """
    @app.errorhandler(RequestValidationError)
    def handle_request_validation_error(error):
        response = {
            'error': 'Validation Error',
            'message': error.message,
        }
        if error.errors:
            response['details'] = error.errors
        return jsonify(response), 400
