# Violation checking logic

from sqlalchemy.orm import Session
from app.models import Vehicle, Violation
from app.schemas import ViolationCheckResult, ViolationResponse
from typing import List, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def check_plate_violations(db: Session, plate_number: str) -> ViolationCheckResult:
    """
    Check if a license plate has any violations in the database
    
    Args:
        db: Database session
        plate_number: License plate number
    
    Returns:
        ViolationCheckResult with all violations found
    """
    try:
        # Normalize plate number
        plate_number = plate_number.strip().upper()
        
        # Query violations for this plate
        violations = db.query(Violation).filter(
            Violation.plate_number == plate_number
        ).all()
        
        # Prepare response
        violation_list = []
        total_fine = 0.0
        last_violation_date = None
        
        for v in violations:
            violation_list.append(ViolationResponse.from_orm(v))
            if v.fine_amount:
                total_fine += v.fine_amount
            if not last_violation_date or v.violation_date > last_violation_date:
                last_violation_date = v.violation_date
        
        result = ViolationCheckResult(
            plate_number=plate_number,
            has_violations=len(violations) > 0,
            violation_count=len(violations),
            violations=violation_list,
            total_fine=total_fine,
            last_violation_date=last_violation_date
        )
        
        logger.info(f"✓ Checked plate {plate_number}: {len(violations)} violations found")
        return result
        
    except Exception as e:
        logger.error(f"Error checking violations for {plate_number}: {e}")
        return ViolationCheckResult(
            plate_number=plate_number,
            has_violations=False,
            violation_count=0,
            violations=[]
        )

def add_violation(
    db: Session,
    plate_number: str,
    violation_type: str,
    violation_date: datetime,
    **kwargs
) -> Tuple[bool, str]:
    """
    Add a new violation to the database
    
    Args:
        db: Database session
        plate_number: License plate number
        violation_type: Type of violation
        violation_date: When violation occurred
        **kwargs: Additional fields (location, speed, etc.)
    
    Returns:
        Tuple of (success, message)
    """
    try:
        violation = Violation(
            plate_number=plate_number.strip().upper(),
            violation_type=violation_type,
            violation_date=violation_date,
            **kwargs
        )
        
        db.add(violation)
        db.commit()
        db.refresh(violation)
        
        logger.info(f"✓ Violation added for plate {plate_number}: {violation_type}")
        return True, f"Violation recorded (ID: {violation.id})"
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding violation: {e}")
        return False, f"Error: {str(e)}"

def register_vehicle(
    db: Session,
    plate_number: str,
    **kwargs
) -> Tuple[bool, str]:
    """
    Register a new vehicle in the database
    
    Args:
        db: Database session
        plate_number: License plate number
        **kwargs: Vehicle details (owner_name, vehicle_type, etc.)
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Check if already exists
        existing = db.query(Vehicle).filter(
            Vehicle.plate_number == plate_number.strip().upper()
        ).first()
        
        if existing:
            return False, "Vehicle already registered"
        
        vehicle = Vehicle(
            plate_number=plate_number.strip().upper(),
            **kwargs
        )
        
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)
        
        logger.info(f"✓ Vehicle registered: {plate_number}")
        return True, f"Vehicle registered (ID: {vehicle.id})"
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error registering vehicle: {e}")
        return False, f"Error: {str(e)}"

def get_vehicle_info(db: Session, plate_number: str) -> dict:
    """Get vehicle information"""
    try:
        vehicle = db.query(Vehicle).filter(
            Vehicle.plate_number == plate_number.strip().upper()
        ).first()
        
        if vehicle:
            return {
                "found": True,
                "id": vehicle.id,
                "plate_number": vehicle.plate_number,
                "vehicle_type": vehicle.vehicle_type,
                "color": vehicle.color,
                "owner_name": vehicle.owner_name,
                "owner_phone": vehicle.owner_phone,
                "is_active": vehicle.is_active
            }
        else:
            return {"found": False, "plate_number": plate_number}
            
    except Exception as e:
        logger.error(f"Error getting vehicle info: {e}")
        return {"found": False, "error": str(e)}
