# =============================
# ADDITIONAL DATA STRUCTURES
# =============================

coupling_groups = {}  # e.g., {1: ["PGT-001", "PGT-002"], 2: ["PGT-003"] }
next_group_id = 1

def create_new_group(unit_ids):
    global next_group_id
    coupling_groups[next_group_id] = unit_ids
    for uid in unit_ids:
        all_units[uid]["group_id"] = next_group_id
    next_group_id += 1

def merge_groups(gid1, gid2):
    # merges group2 into group1
    coupling_groups[gid1].extend(coupling_groups[gid2])
    for uid in coupling_groups[gid2]:
        all_units[uid]["group_id"] = gid1
    del coupling_groups[gid2]

def remove_unit_from_group(unit_id):
    gid = all_units[unit_id]["group_id"]
    if gid is None:
        return
    coupling_groups[gid].remove(unit_id)
    all_units[unit_id]["group_id"] = None
    # If group becomes empty or has 1 unit, handle accordingly

# In each unit dictionary, add:
# "group_id": None

# ==============================
# COUPLING / DECOUPLING LOGIC
# ==============================

def check_coupling_conditions():
    """
    Called each simulation loop BEFORE we do normal movement.
    1) Identify pairs of units with same direction, distance < 270m
    2) If not in the same group, trigger approach speeds
    3) If distance < 10m, reduce trailing speed to 0.5 m/s
    4) If distance < 1m, finalize coupling (group them together)
    """
    # Convert all_units to a list we can iterate
    unit_list = list(all_units.values())

    # We'll do a naive O(n^2) check for demonstration
    for i in range(len(unit_list)):
        for j in range(i+1, len(unit_list)):
            uA = unit_list[i]
            uB = unit_list[j]

            # They must be "moving" or in the same direction at least
            if uA["direction"] != uB["direction"]:
                continue

            # Identify lead vs trail. Assume "up" means higher position is lead.
            # If "down" means lower position is lead.
            if uA["direction"] == "up":
                if uA["position_m"] > uB["position_m"]:
                    lead, trail = uA, uB
                else:
                    lead, trail = uB, uA
            else:  # direction "down"
                if uA["position_m"] < uB["position_m"]:
                    lead, trail = uA, uB
                else:
                    lead, trail = uB, uA

            distance = abs(lead["position_m"] - trail["position_m"])
            if distance > 270:
                continue  # no coupling needed

            # They are within 270m, so let's handle approach
            # If they're already in the same group, skip
            if lead["group_id"] == trail["group_id"] and lead["group_id"] is not None:
                # already coupled or in partial coupling
                continue

            # If not in same group, approach logic
            if distance > 10:
                # set trailing speed to 2.7 m/s if it's not already faster
                if trail["speed_mps"] < 2.7:
                    trail["speed_mps"] = min(2.7, trail["speed_mps"] + 0.5)  # or some increment
            else:
                # distance <= 10
                if distance > 1:
                    # reduce trailing to 0.5 m/s
                    if trail["speed_mps"] > 0.5:
                        trail["speed_mps"] = 0.5
                else:
                    # distance ~ 1 or 0 => finalize coupling
                    finalize_coupling(lead, trail)


def finalize_coupling(lead, trail):
    """
    Once distance is effectively zero, treat them as a single group.
    They share speed, position, etc.
    """
    # Snap trailing unit to lead position if you want zero gap
    trail["position_m"] = lead["position_m"]
    trail["speed_mps"] = lead["speed_mps"]

    # Merge groups or create a new group
    if lead["group_id"] is None and trail["group_id"] is None:
        # create new group with both
        create_new_group([lead["id"], trail["id"]])
    elif lead["group_id"] is not None and trail["group_id"] is None:
        # add trail to lead's group
        gid = lead["group_id"]
        coupling_groups[gid].append(trail["id"])
        trail["group_id"] = gid
    elif lead["group_id"] is None and trail["group_id"] is not None:
        # add lead to trail's group
        gid = trail["group_id"]
        coupling_groups[gid].append(lead["id"])
        lead["group_id"] = gid
    else:
        # both have group_id -> merge the two groups
        if lead["group_id"] != trail["group_id"]:
            merge_groups(lead["group_id"], trail["group_id"])


def check_decoupling_conditions():
    """
    If a leading unit in a group halts or goes to a loop line,
    we decouple trailing units. If a middle unit halts, it splits the group.
    """
    for gid, members in list(coupling_groups.items()):
        # Identify ordering by position
        sorted_units = sorted(members, key=lambda uid: all_units[uid]["position_m"], reverse=False)
        # If direction is down, reverse the sort, etc. We can unify logic if we store direction somewhere.

        # For each unit in the group, check if it decided to stop
        for i, uid in enumerate(sorted_units):
            u = all_units[uid]
            if u["status"] == "anchored" or u["destination"] is None:
                # This unit is halting or about to loop off
                # All units behind it (i+1 to end) must decouple
                trailing_units = sorted_units[i+1:]
                if trailing_units:
                    # create new group or set them each to uncoupled
                    create_new_group(trailing_units)
                    # remove them from old group
                    for t_uid in trailing_units:
                        coupling_groups[gid].remove(t_uid)
                # If the group has only the halting unit left, that’s fine
                break

        # If the group is now empty or only one unit, handle cleanup
        if not coupling_groups[gid]:
            del coupling_groups[gid]
        elif len(coupling_groups[gid]) == 1:
            # single unit left, it's effectively uncoupled
            single_uid = coupling_groups[gid][0]
            all_units[single_uid]["group_id"] = None
            del coupling_groups[gid]


def move_units_with_groups(dt):
    """
    This function updates the position/speed of each group rather than each unit individually.
    If a unit is in a group, it follows the group speed (that of the "leading" unit).
    """
    # 1) Move uncoupled units individually (that have group_id = None).
    # 2) Move each group based on the leading unit's speed + acceleration logic.

    # Let's handle coupling checks first
    check_coupling_conditions()
    check_decoupling_conditions()

    # Then move each group or uncoupled unit
    # Example: For each group, pick the leading unit as speed reference
    for gid, members in coupling_groups.items():
        # pick the leading unit (lowest or highest position_m depending on direction)
        # for simplicity, assume direction "up" => leading = max pos
        leading_unit = max(members, key=lambda uid: all_units[uid]["position_m"])
        lead_obj = all_units[leading_unit]

        # accelerate the lead unit as normal (±1 m/s², block checks, etc.)
        # for demonstration, we just keep speed same or do your existing logic
        # ...
        # update lead_obj["position_m"] = ...
        # Then set all trailing to that position minus zero gap if fully coupled
        for uid in members:
            if uid == leading_unit:
                continue
            all_units[uid]["speed_mps"] = lead_obj["speed_mps"]
            # If you want them physically stacked:
            all_units[uid]["position_m"] = lead_obj["position_m"]  # zero gap

    # Move uncoupled units (group_id=None) with your normal logic
    for unit_id, unit in all_units.items():
        if unit["group_id"] is None:
            # do your normal move logic here (acceleration, block occupancy, etc.)
            pass
