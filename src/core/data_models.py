from dataclasses import dataclass, field
from typing import List, Optional
import datetime
import json

@dataclass
class FrequencyResponseData:
    frequency: List[float]
    magnitude_db: List[float]
    phase_deg: List[float]

@dataclass
class ThdData:
    frequency: List[float]
    thd_percent: List[float]

@dataclass
class ProductInfo:
    brand: str = ""
    model: str = ""
    serial_number: str = ""
    operator: str = ""

@dataclass
class TestResult:
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    product_info: ProductInfo = field(default_factory=ProductInfo)
    calibration_gain: float = 1.0
    calibration_spl: float = 0.0
    
    fr_data: Optional[FrequencyResponseData] = None
    thd_data: Optional[ThdData] = None
    
    def to_json(self):
        """Serialize to JSON string."""
        return json.dumps(self, default=lambda o: o.__dict__, indent=4)

    @staticmethod
    def from_json(json_str):
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        # Reconstruct objects (simplified)
        res = TestResult()
        res.__dict__.update(data)
        return res
