"""HTTP client for the STATSports Third Party API V7."""
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from .config import StatsportSettings


class StatsportAPIError(RuntimeError):
	"""Raised when STATSports returns an invalid or unsuccessful response."""

	def __init__(self, message: str, status_code: int | None = None):
		super().__init__(message)
		self.status_code = status_code


Transport = Callable[[httpx.Request], httpx.Response | Awaitable[httpx.Response]]


class StatsportAPIClient:
	"""Small isolated client for the documented STATSports V7 endpoints."""

	def __init__(
		self,
		settings: StatsportSettings | None = None,
		client: httpx.AsyncClient | None = None,
	) -> None:
		self.settings = settings or StatsportSettings.from_env()
		self._client = client
		self._owns_client = client is None

	async def __aenter__(self) -> "StatsportAPIClient":
		await self._get_client()
		return self

	async def __aexit__(self, exc_type, exc_value, traceback) -> None:
		await self.close()

	async def _get_client(self) -> httpx.AsyncClient:
		if self._client is None:
			self._client = httpx.AsyncClient(timeout=self.settings.timeout_seconds)
		return self._client

	async def close(self) -> None:
		if self._client is not None and self._owns_client:
			await self._client.aclose()
			self._client = None

	def _headers(self) -> dict[str, str]:
		headers = {
			"Accept": "application/json",
			"Content-Type": "application/json",
			"api-version": self.settings.api_version,
		}
		if self.settings.api_token:
			headers["Authorization"] = f"Bearer {self.settings.api_token}"
		return headers

	async def _request(self, method: str, endpoint: str, payload: dict[str, Any] | None = None) -> Any:
		client = await self._get_client()
		try:
			response = await client.request(
				method,
				f"{self.settings.api_base_url}/{endpoint.lstrip('/')}",
				headers=self._headers(),
				json=payload,
			)
		except httpx.HTTPError as exc:
			raise StatsportAPIError(f"STATSports request failed: {exc}") from exc

		if response.status_code >= 400:
			raise StatsportAPIError(
				f"STATSports returned HTTP {response.status_code}",
				status_code=response.status_code,
			)

		try:
			return response.json()
		except ValueError as exc:
			raise StatsportAPIError("STATSports returned invalid JSON", response.status_code) from exc

	async def test(self) -> Any:
		return await self._request("GET", "test")

	async def get_available_metrics(self) -> list[str]:
		result = await self._request("GET", "getAvailableMetrics")
		if not isinstance(result, list) or not all(isinstance(item, str) for item in result):
			raise StatsportAPIError("getAvailableMetrics returned an invalid payload")
		return result

	async def get_full_session(self, third_party_api_id: str, session_date: str | None = None) -> Any:
		return await self._request(
			"POST", "getFullSession",
			{"thirdPartyApiId": third_party_api_id, "sessionDate": session_date},
		)

	async def get_full_sessions_by_date_range(
		self, third_party_api_id: str, session_start_date: str | None = None,
		session_end_date: str | None = None,
	) -> Any:
		return await self._request(
			"POST", "getFullSessionsByDateRange",
			{"thirdPartyApiId": third_party_api_id, "sessionStartDate": session_start_date,
			 "sessionEndDate": session_end_date},
		)

	async def get_full_session_by_share_date(
		self, third_party_api_id: str, share_date: str | None = None,
	) -> Any:
		return await self._request(
			"POST", "getFullSessionByShareDate",
			{"thirdPartyApiId": third_party_api_id, "shareDate": share_date},
		)

	async def get_player_details(self, third_party_api_id: str, session_date: str | None = None) -> Any:
		return await self._request(
			"POST", "getPlayerDetails",
			{"thirdPartyApiId": third_party_api_id, "sessionDate": session_date},
		)

	async def get_session_gps_data(self, third_party_api_id: str, raw_data_id: str, next_page: int = 0) -> Any:
		return await self._request(
			"POST", "getSessionGpsData",
			{"thirdPartyApiId": third_party_api_id, "rawDataId": raw_data_id, "nextPage": next_page},
		)

	async def get_session_imu_data(self, third_party_api_id: str, raw_data_id: str, next_page: int = 0) -> Any:
		return await self._request(
			"POST", "getSessionImuData",
			{"thirdPartyApiId": third_party_api_id, "rawDataId": raw_data_id, "nextPage": next_page},
		)

	async def get_session_raw_data(self, third_party_api_id: str, raw_data_id: str, next_page: int = 0) -> Any:
		return await self._request(
			"POST", "getSessionRawData",
			{"thirdPartyApiId": third_party_api_id, "rawDataId": raw_data_id, "nextPage": next_page},
		)


__all__ = ["StatsportAPIClient", "StatsportAPIError"]