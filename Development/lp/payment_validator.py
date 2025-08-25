import requests
import json
from typing import Optional, Dict, Any

class MetroPaymentValidator:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.endpoint = f"{self.base_url}/ticket-payment/generate-payment-metro"
        
    def validate_payment(self, auth_token: str, pas_id: int) -> Dict[str, Any]:
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {auth_token}" if not auth_token.startswith("Bearer") else auth_token,
            "Content-Type": "application/json"
        }
        
        # Prepare request body
        payload = {
            "pasId": pas_id,
            "ticId": 1
        }
        
        try:
            # Make PUT request
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            # Handle different response scenarios
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Pago validado exitosamente. Ticket descontado.",
                    "remaining_tickets": "Consulte su saldo para ver los tickets restantes"
                }
            
            elif response.status_code == 400:
                # Get error from header
                error_message = response.headers.get('error', 'Error desconocido')
                
                # Map error messages to user-friendly responses in Spanish
                error_mapping = {
                    "Invalid token": "Fallo de autenticación. Por favor inicie sesión nuevamente.",
                    "Ticket not found": "ID de ticket inválido. Por favor verifique su ticket.",
                    "Passenger not found": "Usted no posee este tipo de ticket.",
                    "NOT_ENOUGH_TICKETS_METRO": "Tickets insuficientes. Por favor recargue su tarjeta."
                }
                
                user_message = error_mapping.get(error_message, error_message)
                
                return {
                    "success": False,
                    "error": error_message,
                    "message": user_message
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Código de estado inesperado: {response.status_code}",
                    "message": "Ocurrió un error inesperado. Por favor intente nuevamente."
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Error de conexión. Por favor verifique su conexión a internet."
            }