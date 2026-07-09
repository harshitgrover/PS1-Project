from typing import Any

class ConstraintValidationError(Exception):
    """
    Custom exception raised when user constraints or dimensions violate legal building codes.
    """
    def __init__(self, reasons: list[str]):
        """
        Initializes the validation error with a list of specific reasons.

        Args:
            reasons (list[str]): A list of string messages describing each validation failure.
        """
        self.reasons = reasons
        super().__init__("Constraint validation failed")

class ConstraintValidator:
    """
    Validates structural and user-provided constraints against legal zoning/building codes.
    Ensures that layout requests do not violate setbacks, coverage limits, or basic habitability rules.
    """
    def __init__(self, zoning_data: dict, user_constraints: dict | str, supabase_client: Any):
        """
        Initializes the validator with current zoning data and user constraints.

        Args:
            zoning_data (dict): The raw JSON payload from the location/zoning agent.
            user_constraints (dict | str): The parsed JSON dictionary of user constraints, or a raw string if parsing failed.
            supabase_client (Any): The Supabase database client for fetching legal minimums.
        """
        self.zoning = zoning_data or {}
        if isinstance(user_constraints, str):
            # If user_constraints is a string, it's unstructured text, skip structured validation
            self.user = {}
            self.user_text = user_constraints
        else:
            self.user = user_constraints or {}
            self.user_text = ""
        self.supabase = supabase_client

    def validate(self) -> None:
        """
        Executes the validation checks.
        Validates setbacks, FAR/Lot Coverage, building dimensions, room sizes, and habitability.
        Raises a ConstraintValidationError if any rules are violated.

        Args:
            None

        Returns:
            None
        """
        # We only do structural validation if user provided JSON properties
        if not self.user:
            return
            
        errors = []
        
        # 0. Validate User Overrides dynamically against Supabase Zone Rules
        overrides = self.user.get("overrides", {})
        user_exterior = overrides.get("exterior", {})
        user_interior = overrides.get("interior", {})
        all_user_overrides = {**user_exterior, **user_interior}
        
        # Extract variables robustly from raw zoning payload first
        lot_area = self._extract_float("lot_area", self.zoning)
        lot_width = self._extract_float("lot_width", self.zoning)
        lot_depth = self._extract_float("lot_depth", self.zoning)
        max_far = self._extract_float("max_far", self.zoning)
        max_lot_coverage = self._extract_float("max_lot_coverage", self.zoning)
        max_height = self._extract_float("max_height", self.zoning)
        
        z_front = self._extract_float("front_setback", self.zoning)
        z_rear = self._extract_float("rear_setback", self.zoning)
        z_side = self._extract_float("side_setback", self.zoning)
        
        jurisdiction = self.zoning.get('jurisdiction')
        zone = self.zoning.get('zone_code') or self.zoning.get('zone')
        
        if jurisdiction and zone and self.supabase:
            loc = jurisdiction.replace(", ", "_").replace(" ", "_")
            try:
                res = self.supabase.table("zone_rules").select("rule_key, rule_value").eq("location", loc).eq("zone", zone).execute()
                sb_rules = {row["rule_key"]: row["rule_value"] for row in res.data}
                
                # 1. Validate Overrides dynamically
                for k, v in sb_rules.items():
                    if k in all_user_overrides:
                        user_val = all_user_overrides[k]
                        try:
                            if k.startswith("min_") or k.endswith("_setback_ft") or k.endswith("_margin_ft"):
                                if float(user_val) < float(v):
                                    errors.append(f"Override for {k} ({user_val}) is less than the legal zoning minimum ({v}).")
                            elif k.startswith("max_"):
                                if float(user_val) > float(v):
                                    errors.append(f"Override for {k} ({user_val}) is greater than the legal zoning maximum ({v}).")
                            elif k.startswith("requires_"):
                                if str(v).lower() == "true" and str(user_val).lower() == "false":
                                    errors.append(f"Override for {k} cannot bypass a legally required building/zoning code.")
                        except (ValueError, TypeError):
                            pass
                            
                # 2. Fill missing base variables from Supabase if zoning agent missed them
                if max_far is None: max_far = self._extract_float("max_far", sb_rules)
                if max_lot_coverage is None: max_lot_coverage = self._extract_float("max_lot_coverage_fraction", sb_rules)
                if max_height is None: max_height = self._extract_float("max_height_ft", sb_rules)
                if z_front is None: z_front = self._extract_float("front_setback_ft", sb_rules)
                if z_rear is None: z_rear = self._extract_float("rear_setback_ft", sb_rules)
                if z_side is None: z_side = self._extract_float("side_setback_ft", sb_rules)
            except Exception:
                pass
        
        # User requested setbacks
        u_front = self._extract_float("front_setback", self.user)
        u_rear = self._extract_float("rear_setback", self.user)
        u_side = self._extract_float("side_setback", self.user)
        
        # 1. Base Setback Violations (using explicit checks if available in zoning JSON)
        # Some location agents might return setbacks in the base JSON rather than Supabase
        if u_front is not None and z_front is not None and u_front < z_front:
            errors.append(f"Requested front setback ({u_front}ft) is less than the legal minimum ({z_front}ft).")
        if u_rear is not None and z_rear is not None and u_rear < z_rear:
            errors.append(f"Requested rear setback ({u_rear}ft) is less than the legal minimum ({z_rear}ft).")
        if u_side is not None and z_side is not None and u_side < z_side:
            errors.append(f"Requested side setback ({u_side}ft) is less than the legal minimum ({z_side}ft).")
            
        # 2. Total Area vs Buildable Area
        max_buildable_area = None
        if lot_area is not None:
            if max_far is not None:
                max_buildable_area = lot_area * max_far
            elif max_lot_coverage is not None:
                max_buildable_area = lot_area * max_lot_coverage
                
        total_requested_area = 0
        required_instances = self.user.get("required_instances", [])
        room_overrides = self.user.get("room_overrides", {})
        
        # Habitability checks (1 bathroom, 1 kitchen, 1 bedroom)
        if self.user and required_instances:  # Only enforce if user gave structured input
            # Helper to extract base type consistently
            def get_base(name):
                for b in ["bedroom", "bathroom", "kitchen", "living", "corridor", "dining", "garage", "laundry", "entry", "balcony"]:
                    if b in name: return b
                return name.rsplit('_', 1)[0]
                
            base_types = [get_base(inst) for inst in required_instances]
            if "bathroom" not in base_types:
                errors.append("Habitability Violation: At least 1 bathroom is required by building codes.")
            if "kitchen" not in base_types:
                errors.append("Habitability Violation: At least 1 kitchen is required by building codes.")
            if "bedroom" not in base_types:
                errors.append("Habitability Violation: At least 1 bedroom is required by building codes.")

        if isinstance(required_instances, list):
            for inst in required_instances:
                # Same base extraction
                ent_type = None
                for b in ["bedroom", "bathroom", "kitchen", "living", "corridor", "dining", "garage", "laundry", "entry", "balcony"]:
                    if b in inst: 
                        ent_type = b
                        break
                if not ent_type:
                    ent_type = inst.rsplit('_', 1)[0]
                    
                req_area = None
                
                # Check overrides
                if inst in room_overrides:
                    user_or = room_overrides[inst]
                    if "min_area_ft2" in user_or:
                        req_area = float(user_or["min_area_ft2"])
                
                if req_area:
                    total_requested_area += req_area
                    # Validate against legal minimums
                    if ent_type and self.supabase:
                        try:
                            res = self.supabase.table("entity_specs").select("min_area_ft2").eq("entity_type", ent_type).execute()
                            if res.data and res.data[0].get("min_area_ft2"):
                                min_legal = float(res.data[0]["min_area_ft2"])
                                if req_area < min_legal:
                                    errors.append(f"Requested area ({req_area} sqft) for {inst} is less than the legal building code minimum ({min_legal} sqft).")
                        except Exception:
                            pass
                else:
                    if ent_type and self.supabase:
                        try:
                            res = self.supabase.table("entity_specs").select("min_area_ft2").eq("entity_type", ent_type).execute()
                            if res.data and res.data[0].get("min_area_ft2"):
                                total_requested_area += float(res.data[0]["min_area_ft2"])
                        except Exception:
                            pass

        if max_buildable_area and total_requested_area > max_buildable_area:
            errors.append(f"Total requested room area ({total_requested_area} sqft) exceeds the maximum legal buildable area ({max_buildable_area} sqft) based on FAR/Coverage limits.")

        # 3. Room Dimensions vs Buildable Plot Dimensions
        if lot_width and lot_depth:
            safe_side = z_side or 0
            safe_front = z_front or 0
            safe_rear = z_rear or 0
            buildable_width = lot_width - (2 * safe_side)
            buildable_depth = lot_depth - safe_front - safe_rear
            
            if isinstance(required_instances, list):
                for inst in required_instances:
                    if inst in room_overrides:
                        user_or = room_overrides[inst]
                        min_s = user_or.get("min_side_ft")
                        max_s = user_or.get("max_side_ft")
                        if min_s is not None:
                            max_avail = max(buildable_width, buildable_depth)
                            if min_s > max_avail:
                                errors.append(f"Requested minimum dimension {min_s}ft for {inst} exceeds the buildable plot footprint (approx {buildable_width}ft x {buildable_depth}ft).")
                                
                            # Check explicit max aspect ratio contradiction
                            if min_s > 0 and max_s is not None:
                                req_ar = max_s / min_s
                                explicit_max_ar = user_or.get("max_aspect_ratio")
                                if explicit_max_ar is not None and req_ar > explicit_max_ar:
                                    errors.append(f"User contradiction: Requested sides require an aspect ratio of {req_ar:.2f}, but user explicitly capped max_aspect_ratio at {explicit_max_ar}.")

        # 4. Height & Story Limits
        u_stories = self._extract_float("stories", self.user)
        if u_stories and max_height:
            estimated_height = u_stories * 10
            if estimated_height > max_height:
                errors.append(f"Requested {u_stories} stories (approx {estimated_height}ft) exceeds the legal zoning height limit of {max_height}ft.")

        if errors:
            raise ConstraintValidationError(errors)

    def _extract_float(self, key: str, d: dict) -> float | None:
        """
        Safely extracts a float value from a dictionary.

        Args:
            key (str): The key to lookup.
            d (dict): The dictionary to search in.

        Returns:
            float | None: The parsed float value, or None if missing/invalid.
        """
        if not isinstance(d, dict):
            return None
        val = d.get(key)
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
