"""Réponses classique pour fastAPI."""

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

ok_response: JSONResponse = JSONResponse(content=jsonable_encoder(obj={"status": "OK"}))
