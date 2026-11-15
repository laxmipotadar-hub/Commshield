from fastapi import APIRouter

from ..schemas import DatasetListResponse
from ..services.sample_data import get_sample_datasets

router = APIRouter(tags=["Datasets"])


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets() -> DatasetListResponse:
    """List available public and testbed traces."""
    # TODO: In milestone M1/M6, query active dataset catalog / storage adapters for dynamic dataset list
    return get_sample_datasets()
