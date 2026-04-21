import math
import calendar
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from gantt_chart import create_gantt_chart

class Location:
    def __init__(self, name, planned_advance, progress_rate, waste_per_meter, waste_capacity_per_shift=125.7112, activity_type="tunneling", blast_days=None):
        self.name = name
        self.planned_advance = planned_advance
        self.progress_rate = progress_rate  # m/blast for rm_blasting, m/shift for tunneling
        self.waste_per_meter = waste_per_meter  # Tons/m, 2 decimals
        self.waste_capacity_per_shift = waste_capacity_per_shift  # Tons/shift, adjusted later
        self.activity_type = activity_type  # "rm_blasting" or "tunneling"
        self.blast_days = blast_days if activity_type == "rm_blasting" else None  # Days per blast for rm_blasting
        self.progress = {}
        self.units = {}  # blasts for rm_blasting, shifts for tunneling
        self.presence = {}
        self.tasks = {}  # Store start, duration, end, interval
        self.unavailable_months = []
        self.max_required_shifts = math.ceil(self.planned_advance / self.progress_rate)
        self.cumulative_shifts = None
        self.cumulative_progress_var = None  # Track cumulative progress

    def set_unavailable_months(self, months):
        self.unavailable_months = months
        print(f"Set unavailable months for {self.name}: {self.unavailable_months}")

    def setup_task(self, model, month, days_in_month, shifts_per_day, schedule, all_locations):
        shifts = days_in_month * shifts_per_day  # Custom shifts per day
        if month in self.unavailable_months:
            progress_var = model.NewIntVar(0, 0, f"progress_{self.name}_{month}")
            unit_var = model.NewIntVar(0, 0, f"units_{self.name}_{month}")
            presence_var = model.NewBoolVar(f"presence_{self.name}_{month}")
            start_var = model.NewIntVar(0, 0, f"start_{self.name}_{month}")
            duration_var = model.NewIntVar(0, 0, f"duration_{self.name}_{month}")
            end_var = model.NewIntVar(0, 0, f"end_{self.name}_{month}")
            waste_capacity_month_var = model.NewIntVar(0, 0, f"waste_capacity_month_{self.name}_{month}")
            model.Add(progress_var == 0)
            model.Add(unit_var == 0)
            model.Add(presence_var == 0)
            model.Add(start_var == 0)
            model.Add(duration_var == 0)
            model.Add(end_var == 0)
            model.Add(waste_capacity_month_var == 0)
        else:
            max_shifts = shifts
            progress_var = model.NewIntVar(0, int((self.planned_advance + math.ceil(self.progress_rate)) * 1000), f"progress_{self.name}_{month}")  # mm
            presence_var = model.NewBoolVar(f"presence_{self.name}_{month}")
            start_var = model.NewIntVar(0, max_shifts, f"start_{self.name}_{month}")
            duration_var = model.NewIntVar(0, max_shifts, f"duration_{self.name}_{month}")
            end_var = model.NewIntVar(0, max_shifts, f"end_{self.name}_{month}")
            if self.activity_type == "rm_blasting":
                max_units = math.floor(days_in_month / self.blast_days)  # Max blasts based on blast_days
                unit_var = model.NewIntVar(0, max_units, f"blasts_{self.name}_{month}")
                model.Add(progress_var == unit_var * int(self.progress_rate * 1000))  # mm/blast
                print(f"Constrained {self.name} in {month}: max {max_units} blasts (days_in_month={days_in_month}, blast_days={self.blast_days})")
            else:  # tunneling
                max_units = max_shifts
                unit_var = model.NewIntVar(0, max_units, f"shifts_{self.name}_{month}")
                model.Add(progress_var == unit_var * int(self.progress_rate * 1000))  # mm/shift
            model.Add(unit_var > 0).OnlyEnforceIf(presence_var)
            model.Add(unit_var == 0).OnlyEnforceIf(presence_var.Not())
            model.Add(duration_var == unit_var)  # Duration = units (blasts or shifts)
            model.Add(end_var == start_var + duration_var)
            # Waste capacity per month = waste_capacity_per_shift * duration
            waste_capacity_month_var = model.NewIntVar(0, int(self.waste_capacity_per_shift * 100 * max_shifts), f"waste_capacity_month_{self.name}_{month}")
            model.Add(waste_capacity_month_var == duration_var * int(self.waste_capacity_per_shift * 100))
        interval_var = model.NewOptionalIntervalVar(start_var, duration_var, end_var, presence_var, f"interval_{self.name}_{month}")
        self.progress[month] = progress_var
        self.units[month] = unit_var
        self.presence[month] = presence_var
        self.tasks[month] = {
            'start': start_var,
            'duration': duration_var,
            'end': end_var,
            'presence': presence_var,
            'interval': interval_var,
            'waste_capacity_month': waste_capacity_month_var
        }
        if self.cumulative_shifts is None:
            self.cumulative_shifts = []
        self.cumulative_shifts.append(unit_var)
        print(f"Created {self.activity_type} task for {self.name} in {month}: start=[{start_var.Proto().domain[0]},{start_var.Proto().domain[-1]}] shifts, duration=[{duration_var.Proto().domain[0]},{duration_var.Proto().domain[-1]}] shifts, progress=[{progress_var.Proto().domain[0]/1000:.3f},{progress_var.Proto().domain[-1]/1000:.3f}] meters")

    def finalize_constraints(self, model):
        if self.cumulative_shifts:
            model.Add(sum(self.cumulative_shifts) <= self.max_required_shifts)
            print(f"Added constraint for {self.name}: Total required shifts <= {self.max_required_shifts}")

class Equipment:
    def __init__(self, name, max_units):
        self.name = name
        self.max_units = max_units
        self.drill_names = [f"Jackleg {i+1}" for i in range(max_units)] if name == "Jackleg Drill" else [name] * max_units

    def allocate(self, model, locations, month, days_in_month, shifts_per_day, drill_demand_per_location):
        max_shifts = days_in_month * shifts_per_day
        if self.name == "Jackleg Drill":
            rm_blasting_locations = [loc for loc in locations if loc.activity_type == "rm_blasting"]
            tunneling_locations = [loc for loc in locations if loc.activity_type == "tunneling"]
            total_units = sum(loc.units[month] for loc in rm_blasting_locations + tunneling_locations)
            model.Add(total_units <= self.max_units * days_in_month * shifts_per_day)
            intervals = [loc.tasks[month]['interval'] for loc in rm_blasting_locations + tunneling_locations]
            demands = [drill_demand_per_location] * len(intervals)  # Custom demand per location
            if intervals:
                model.AddCumulative(intervals, demands, self.max_units)
                print(f"Added cumulative constraint for {self.name} in {month}: max {self.max_units} overlapping tasks with demand {drill_demand_per_location} per location")
            if rm_blasting_locations or tunneling_locations:
                print(f"Allocated {self.name} for {month}: max {self.max_units * days_in_month * shifts_per_day} drill-day-shifts for tunneling and rm_blasting")
        else:
            print(f"Allocated {self.name} for {month}: max {self.max_units} units")  # No presence constraint

class Schedule:
    def __init__(self, start_year, start_month, end_year=None, end_month=None, shifts_per_day=2, drill_demand_per_location=1, min_tunnel_progress=38.4):
        self.start_year = start_year
        self.start_month = start_month
        self.end_year = end_year
        self.end_month = end_month
        self.shifts_per_day = shifts_per_day  # Custom shifts per day
        self.drill_demand_per_location = drill_demand_per_location  # Custom drill demand per location
        self.min_tunnel_progress = min_tunnel_progress  # Minimum total tunneling progress per month (meters, 3 decimals)
        self.months = []
        self.days_per_month = {}
        self.shifts_per_month = {}
        self.model = cp_model.CpModel()
        self.locations = []
        self.jackleg_drill = None
        self.jackleg_units = 0
        self.wheel_loader = None
        self.wheel_loader_units = 0

    def add_location(self, location):
        self.locations.append(location)
        print(f"Added location: {location.name}")

    def add_equipment(self, equipment):
        if equipment.name == "Jackleg Drill":
            self.jackleg_drill = equipment
            self.jackleg_units = equipment.max_units
        elif equipment.name == "Wheel Loader":
            self.wheel_loader = equipment
            self.wheel_loader_units = equipment.max_units
        print(f"Added equipment: {equipment.name}")
        if self.jackleg_drill and self.wheel_loader and self.locations:
            if self.jackleg_units > 0:
                waste_capacity_factor = self.wheel_loader_units / self.jackleg_units
                for location in self.locations:
                    original_capacity = location.waste_capacity_per_shift
                    location.waste_capacity_per_shift = original_capacity * waste_capacity_factor
                    print(f"Adjusted waste capacity per shift for {location.name}: {location.waste_capacity_per_shift:.4f} tons/shift (factor: {waste_capacity_factor:.2f})")
            else:
                print("Error: Jackleg Drill units must be greater than 0 to adjust waste capacity")

    def setup_model(self):
        print("Setting up CP model...")
        if not self.jackleg_drill or not self.locations:
            raise ValueError("Jackleg Drill and locations must be added before setup_model")

        total_shifts = sum(math.ceil(loc.planned_advance / loc.progress_rate) for loc in self.locations)

        year = self.start_year
        month = self.start_month
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
        if self.end_year is not None and self.end_month is not None:
            end_date = (self.end_year, self.end_month)
            while (year, month) <= end_date:
                days = calendar.monthrange(year, month)[1]
                month_key = (month_names[month - 1], year)
                self.months.append(month_key)
                self.days_per_month[month_key] = days
                self.shifts_per_month[month_key] = days * self.shifts_per_day
                month += 1
                if month > 12:
                    month = 1
                    year += 1
        else:
            required_days = total_shifts / (self.jackleg_drill.max_units * self.shifts_per_day)
            available_days = 0
            while available_days < required_days:
                days = calendar.monthrange(year, month)[1]
                month_key = (month_names[month - 1], year)
                self.months.append(month_key)
                self.days_per_month[month_key] = days
                self.shifts_per_month[month_key] = days * self.shifts_per_day
                available_days += days
                month += 1
                if month > 12:
                    month = 1
                    year += 1

        for month_key in self.months:
            days = self.days_per_month[month_key]
            for location in self.locations:
                location.setup_task(self.model, month_key, days, self.shifts_per_day, self, self.locations)

        for location in self.locations:
            location.finalize_constraints(self.model)

        # Minimum total tunneling progress constraint
        for month_key in self.months:
            tunneling_locations = [loc for loc in self.locations if loc.activity_type == "tunneling" and month_key not in loc.unavailable_months]
            if tunneling_locations:
                total_tunnel_progress = sum(loc.progress[month_key] for loc in tunneling_locations)
                self.model.Add(total_tunnel_progress >= int(self.min_tunnel_progress * 1000))
                print(f"Added min tunnel progress constraint for {month_key}: total progress >= {self.min_tunnel_progress:.3f} m")

        for month_key in self.months:
            waste_vars = []
            waste_capacity_month_vars = []
            for location in self.locations:
                loc_waste = self.model.NewIntVar(0, int(location.waste_capacity_per_shift * 100 * location.tasks[month_key]['duration'].Proto().domain[-1]), f"waste_{location.name}_{month_key}")
                temp_waste = self.model.NewIntVar(0, int(location.waste_capacity_per_shift * 100 * 1000 * location.tasks[month_key]['duration'].Proto().domain[-1]), f"temp_waste_{location.name}_{month_key}")
                self.model.Add(temp_waste == location.progress[month_key] * int(location.waste_per_meter * 100))
                self.model.AddDivisionEquality(loc_waste, temp_waste, 1000)
                waste_vars.append(loc_waste)
                waste_capacity_month_vars.append(location.tasks[month_key]['waste_capacity_month'])
            total_waste = self.model.NewIntVar(0, int(sum(loc.waste_capacity_per_shift * loc.tasks[month_key]['duration'].Proto().domain[-1] for loc in self.locations) * 100), f"total_waste_{month_key}")
            self.model.Add(total_waste == sum(waste_vars))
            total_waste_capacity = self.model.NewIntVar(0, int(sum(loc.waste_capacity_per_shift * loc.tasks[month_key]['duration'].Proto().domain[-1] for loc in self.locations) * 100), f"total_waste_capacity_{month_key}")
            self.model.Add(total_waste_capacity == sum(waste_capacity_month_vars))

        for month_key in self.months:
            days = self.days_per_month[month_key]
            self.jackleg_drill.allocate(self.model, self.locations, month_key, days, self.shifts_per_day, self.drill_demand_per_location)
            self.wheel_loader.allocate(self.model, self.locations, month_key, days, self.shifts_per_day, self.drill_demand_per_location)

        # Modified weighting algorithm to prioritize earlier starts for higher-priority locations
        location_weights = {loc.name: len(self.locations) - i for i, loc in enumerate(self.locations)}
        month_weights = {month_key: len(self.months) - i for i, month_key in enumerate(self.months)}
        print(f"Location weights: {location_weights}")
        print(f"Month weights: {month_weights}")
        objective_terms = []
        penalty_weight = 0.01  # Small weight to balance progress (mm) and start (shifts)
        for location in self.locations:
            for month_key in self.months:
                weight = location_weights[location.name] * month_weights[month_key]
                objective_terms.append(weight * location.progress[month_key] - penalty_weight * location_weights[location.name] * location.tasks[month_key]['start'])
        self.model.Maximize(sum(objective_terms))

    def solve(self):
        print("Solving CP model...")
        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)
        gantt_data = []

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            print("Status: Optimal or Feasible")
            total_progress = 0
            rm_progress = 0
            tunnel_progress = 0
            completed_locations = set()
            location_cumulative_progress = {loc.name: 0.0 for loc in self.locations}

            for location in self.locations:
                loc_progress = sum(solver.Value(location.progress[month_key]) for month_key in self.months) / 1000
                total_progress += loc_progress
                if location.activity_type == "rm_blasting":
                    rm_progress += loc_progress
                else:  # tunneling
                    tunnel_progress += loc_progress
                print(f"\nTotal Kemajuan {location.name} (m): {loc_progress:.3f}")

            print(f"\nTotal Kemajuan Semua Lokasi (m): {total_progress:.3f}")
            print(f"Total Kemajuan RM (m): {rm_progress:.3f}")
            print(f"Total Kemajuan Tunneling (m): {tunnel_progress:.3f}")

            incomplete_locations = []
            required_drill_shifts = 0
            available_drill_shifts = sum(self.jackleg_drill.max_units * days * self.shifts_per_day for days in self.days_per_month.values())
            for location in self.locations:
                loc_progress = sum(solver.Value(location.progress[month_key]) for month_key in self.months) / 1000
                if loc_progress < location.planned_advance:
                    incomplete_locations.append((location.name, location.planned_advance, loc_progress))
                    remaining_meters = location.planned_advance - loc_progress
                    drill_shifts = math.ceil((remaining_meters / location.progress_rate) * self.shifts_per_day)
                    required_drill_shifts += drill_shifts

            if incomplete_locations:
                remaining_drill_shifts = required_drill_shifts
                avg_days_per_month = sum(self.days_per_month.values()) / len(self.months)
                avg_shifts_per_month = avg_days_per_month * self.shifts_per_day * self.jackleg_drill.max_units
                additional_months = math.ceil(remaining_drill_shifts / avg_shifts_per_month)
                print(f"\nWarning: The following locations are incomplete:")
                for name, target, achieved in incomplete_locations:
                    print(f"- {name}: Target {target:.3f} m, Achieved {achieved:.3f} m")
                print(f"Additional months required: {additional_months:.1f} (approx., assuming {avg_days_per_month:.1f} days/month)")
            else:
                print("\nAll locations completed within the scheduled months.")

            month_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'Mei': 5, 'Jun': 6, 'Jul': 7, 'Agu': 8, 'Sep': 9, 'Okt': 10, 'Nov': 11, 'Des': 12}
            for month_key in self.months:
                month_name, year = month_key
                month_num = month_map[month_name]
                month_start = datetime(year, month_num, 1)
                monthly_progress = 0
                monthly_rm_progress = 0
                monthly_tunnel_progress = 0
                monthly_rm_blasts = 0
                monthly_tunnel_shifts = 0
                monthly_material = 0
                monthly_capacity = 0
                # Assign drills based on shift usage
                max_shifts_per_drill = self.days_per_month[month_key] * self.shifts_per_day
                drill_assignments = {}
                active_locations = [(loc, solver.Value(loc.units[month_key])) for loc in self.locations if solver.Value(loc.progress[month_key]) >= 0.001]
                active_locations.sort(key=lambda x: x[1], reverse=True)
                used_shifts = 0
                for i, (loc, shifts) in enumerate(active_locations):
                    if i == 0 and shifts == max_shifts_per_drill:
                        drill_assignments[loc.name] = self.jackleg_drill.drill_names[0]  # Jackleg 1
                    else:
                        drill_assignments[loc.name] = self.jackleg_drill.drill_names[1] if len(self.jackleg_drill.drill_names) > 1 else self.jackleg_drill.drill_names[0]
                    used_shifts += shifts
                print(f"\nBulan: {month_name} {year}")
                temp_gantt_data = []
                for location in self.locations:
                    progress_val = solver.Value(location.progress[month_key]) / 1000
                    if progress_val >= 0.001:
                        waste = round(progress_val * location.waste_per_meter, 2)
                        waste_capacity_month = solver.Value(location.tasks[month_key]['waste_capacity_month']) / 100
                        start_shifts = solver.Value(location.tasks[month_key]['start'])
                        duration_shifts = solver.Value(location.tasks[month_key]['duration'])
                        end_shifts = solver.Value(location.tasks[month_key]['end'])
                        start_days = start_shifts / self.shifts_per_day
                        duration_days = duration_shifts / self.shifts_per_day if location.activity_type == "tunneling" else duration_shifts * location.blast_days
                        start_date = (month_start + timedelta(days=start_days)).strftime("%Y-%m-%d")
                        output_str = f"{location.name}: {progress_val:.3f} m, Material: {waste:.2f} ton, Capacity: {waste_capacity_month:.2f} ton (duration: {duration_shifts} shifts, start: {start_shifts} shifts, end: {end_shifts} shifts, using {drill_assignments.get(location.name, 'No Drill')})"
                        if location.activity_type == "rm_blasting":
                            monthly_rm_progress += progress_val
                            monthly_rm_blasts += duration_shifts
                            max_blasts = math.floor(self.days_per_month[month_key] / location.blast_days)
                            duration_days = self.days_per_month[month_key] if duration_shifts == max_blasts else duration_shifts * location.blast_days
                            start_days = start_shifts / self.shifts_per_day
                            start_date = (month_start + timedelta(days=start_days)).strftime("%Y-%m-%d")
                        else:
                            monthly_tunnel_progress += progress_val
                            monthly_tunnel_shifts += duration_shifts
                        monthly_material += waste
                        monthly_capacity += waste_capacity_month
                        location_cumulative_progress[location.name] += progress_val
                        completed = (location.name not in completed_locations and 
                                     location_cumulative_progress[location.name] >= location.planned_advance)
                        if completed:
                            output_str += " (Completed)"
                            completed_locations.add(location.name)
                        print(output_str)
                        monthly_progress += progress_val
                        temp_gantt_data.append({
                            "task_name": f"{location.name} {location.activity_type.capitalize()}",
                            "start_date": start_date,
                            "duration_days": duration_days,
                            "location": location.name,
                            "progress_meters": progress_val,
                            "completed": completed,
                            "activity_type": location.activity_type.capitalize(),
                            "drill_used": drill_assignments.get(location.name, "No Drill"),
                            "start_shifts": start_shifts,
                            "duration_shifts": duration_shifts
                        })
                for drill_name in self.jackleg_drill.drill_names:
                    drill_locations = [(entry, entry["duration_shifts"], solver.Value(self.locations[[l.name for l in self.locations].index(entry["location"])].tasks[month_key]['start'])) 
                                      for entry in temp_gantt_data if entry["drill_used"] == drill_name]
                    drill_locations.sort(key=lambda x: x[2])
                    rm_entry = next((entry for entry, shifts, start in drill_locations if entry["activity_type"] == "Rm_blasting"), None)
                    if rm_entry:
                        rm_index = [entry for entry, _, _ in drill_locations].index(rm_entry)
                        rm_shifts = rm_entry["duration_shifts"]
                        rm_start_shifts = rm_entry["start_shifts"]
                        rm_duration_days = rm_shifts / self.shifts_per_day
                        if rm_index < len(drill_locations) - 1:
                            next_entry = drill_locations[rm_index + 1][0]
                            next_entry["start_shifts"] = rm_start_shifts
                            next_entry["start_date"] = (month_start + timedelta(days=rm_start_shifts / self.shifts_per_day)).strftime("%Y-%m-%d")
                            next_entry["duration_days"] += rm_duration_days
                        elif rm_index == len(drill_locations) - 1 and len(drill_locations) > 1:
                            prev_entry = drill_locations[rm_index - 1][0]
                            prev_entry["duration_days"] += rm_duration_days
                for entry in temp_gantt_data:
                    gantt_data.append({
                        "task_name": entry["task_name"],
                        "start_date": entry["start_date"],
                        "duration_days": entry["duration_days"],
                        "location": entry["location"],
                        "progress_meters": entry["progress_meters"],
                        "completed": entry["completed"],
                        "activity_type": entry["activity_type"],
                        "drill_used": entry["drill_used"]
                    })
                print(f"Total Progress: {monthly_progress:.3f} m")
                print(f"Material / Capacity: {monthly_material:.2f} ton / {monthly_capacity:.2f} ton")
                print(f"RM Progress: {monthly_rm_progress:.3f} m")
                print(f"Tunneling Progress: {monthly_tunnel_progress:.3f} m (min {self.min_tunnel_progress:.1f} m)")
                drill_shift_used = monthly_rm_blasts * 1 + monthly_tunnel_shifts
                drill_shift_max = self.jackleg_drill.max_units * self.days_per_month[month_key] * self.shifts_per_day
                status_str = "Optimal" if drill_shift_used == drill_shift_max else f"Not Optimal"
                print(f"{status_str} ({drill_shift_used}/{drill_shift_max} shifts)")
        else:
            print("Status: Tidak Optimal")
            print("Tidak ditemukan solusi layak.")

        return gantt_data

if __name__ == "__main__":
    schedule = Schedule(start_year=2025, start_month=4, end_year=2025, end_month=6, shifts_per_day=2, drill_demand_per_location=1, min_tunnel_progress=38.4)

    blok4 = Location("B4C", 37.700, round(0.8305 / 2, 3), 57.19, waste_capacity_per_shift=36.14, activity_type="tunneling")
    connect_rm78 = Location("CRM7-8", 8.000, round(0.8305 / 2, 3), 61.56, waste_capacity_per_shift=46.28, activity_type="tunneling")
    rm8 = Location("RM8", 24.230, 1.283, 25.834, waste_capacity_per_shift=30.64, activity_type="rm_blasting", blast_days=3)
    rampdown = Location("RDAS", 147.800, round(0.8305 / 2, 3), 61.56, waste_capacity_per_shift=30.03, activity_type="tunneling")
    rc6 = Location("RC6C", 509.600, round(0.8305 / 2, 3), 56.3, waste_capacity_per_shift=49.17, activity_type="tunneling")

    rc6.set_unavailable_months([("Apr", 2025)])

    schedule.add_location(blok4)
    schedule.add_location(connect_rm78)
    schedule.add_location(rm8)
    schedule.add_location(rampdown)
    schedule.add_location(rc6)

    schedule.add_equipment(Equipment("Jackleg Drill", 2))
    schedule.add_equipment(Equipment("Wheel Loader", 2))

    schedule.setup_model()
    gantt_data = schedule.solve()
    print("\nGantt Chart Data:")
    for task in gantt_data:
        print(task)
    create_gantt_chart(gantt_data)