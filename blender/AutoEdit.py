import bpy
import re
import os

def main():
    scene = bpy.context.scene
    se = scene.sequence_editor
    
    # --- CONFIGURATION ---
    # We put Response audio on Channel 1 (The Floor) to prevent collisions.
    RESPONSE_CHANNEL = 1 
    # We define a "Sky Hook" channel to move clips safely out of the way before placing them
    SAFE_HIGH_CHANNEL = 12
    # ---------------------

    if not se:
        print("No Sequence Editor found.")
        return
        
    blend_file_path = bpy.path.abspath("//")
    if not blend_file_path:
        print("ERROR: Please save your .blend file first.")
        return

    # -------------------------------------------------------------------------
    # STEP 0: PRE-MAPPING (Snapshot the Board)
    # -------------------------------------------------------------------------
    # We memorize the channel of EVERY strip before we touch anything.
    # This is our source of truth.
    original_channel_map = {}
    for s in se.sequences_all:
        original_channel_map[s.name] = s.channel

    # -------------------------------------------------------------------------
    # STEP 1: Scan Markers
    # -------------------------------------------------------------------------
    start_markers = {}
    end_markers = {}
    
    p_start = re.compile(r"^START_(\w+)$")
    p_end = re.compile(r"^END_(\w+)$")

    for m in scene.timeline_markers:
        s_match = p_start.match(m.name)
        e_match = p_end.match(m.name)
        if s_match:
            start_markers[s_match.group(1)] = m.frame
        elif e_match:
            end_markers[e_match.group(1)] = m.frame

    valid_ranges = []
    cut_points = set()
    
    for uid, start_frame in start_markers.items():
        if uid in end_markers:
            end_frame = end_markers[uid]
            if start_frame < end_frame:
                valid_ranges.append({'id': uid, 'start': start_frame, 'end': end_frame})
                cut_points.add(start_frame)
                cut_points.add(end_frame)

    valid_ranges.sort(key=lambda x: x['start'])
    sorted_cut_points = sorted(list(cut_points))

    if not valid_ranges:
        print("No valid START/END pairs found.")
        return

    # -------------------------------------------------------------------------
    # STEP 2: HARD CUTS
    # -------------------------------------------------------------------------
    
    vse_area = None
    vse_region = None
    for area in bpy.context.screen.areas:
        if area.type == 'SEQUENCE_EDITOR':
            vse_area = area
            for region in area.regions:
                if region.type == 'WINDOW':
                    vse_region = region
                    break
            break
            
    if not vse_area:
        print("ERROR: Video Sequencer not found.")
        return

    with bpy.context.temp_override(window=bpy.context.window, area=vse_area, region=vse_region, scene=scene):
        bpy.ops.sequencer.select_all(action='DESELECT')
        for cut_frame in sorted_cut_points:
            strips_to_cut = []
            for strip in se.sequences_all:
                if strip.frame_final_start < cut_frame < (strip.frame_final_start + strip.frame_final_duration):
                    strips_to_cut.append(strip)
            
            if strips_to_cut:
                bpy.ops.sequencer.select_all(action='DESELECT')
                for s in strips_to_cut:
                    s.select = True
                try:
                    bpy.ops.sequencer.split(frame=cut_frame, type='SOFT', side='BOTH')
                except Exception as e:
                    print(f"Split warning at {cut_frame}: {e}")

    # -------------------------------------------------------------------------
    # STEP 3: Cleanup & Regrouping
    # -------------------------------------------------------------------------
    
    range_groups = {r['id']: [] for r in valid_ranges}
    survivors = []
    
    sequences_to_check = list(se.sequences_all)
    
    for strip in sequences_to_check:
        mid_point = strip.frame_final_start + (strip.frame_final_duration / 2)
        keep_strip = False
        assigned_id = None
        
        for r in valid_ranges:
            if r['start'] <= mid_point <= r['end']:
                keep_strip = True
                assigned_id = r['id']
                break
        
        if keep_strip:
            # Look up the ORIGINAL channel from our Step 0 map.
            # Even if the split renamed the strip (e.g., .001), Blender usually 
            # keeps the channel. But safely, we just grab current channel 
            # if name lookup fails, assuming split didn't move it yet.
            target_chan = strip.channel
            
            # If the name exists in our pre-map, use that (safest)
            # Note: Splits create new names, so we might have to rely on current 
            # channel, which is fine because splits don't change channels, moves do.
            range_groups[assigned_id].append({'strip': strip, 'chan': target_chan})
            survivors.append(strip)
        else:
            se.sequences.remove(strip)

    # -------------------------------------------------------------------------
    # STEP 4: Assembly & Vertical Enforcement
    # -------------------------------------------------------------------------
    
    current_write_head = 1
    new_response_strips = []
    
    print("Beginning Assembly...")

    for r in valid_ranges:
        uid = r['id']
        group_data = range_groups[uid]
        
        if not group_data:
            continue

        # --- A. Shift Original Block ---
        strips_in_group = [d['strip'] for d in group_data]
        group_start = min(s.frame_final_start for s in strips_in_group)
        group_end = max(s.frame_final_start + s.frame_final_duration for s in strips_in_group)
        group_len = group_end - group_start
        
        offset = current_write_head - group_start
        
        for item in group_data:
            s = item['strip']
            target_channel = item['chan']
            
            # 1. Lift to Safe Zone (Prevents collision with Response on Ch 1)
            # We move it high up so it doesn't get snagged on anything
            s.channel = SAFE_HIGH_CHANNEL
            
            # 2. Move Horizontally
            s.frame_start = int(s.frame_start + offset)
            
            # 3. Drop to Target (The "Hammer" approach)
            # We immediately force it back to 4/5
            s.channel = target_channel

        current_write_head += group_len
        
        # --- B. Insert RESPONSE Audio ---
        wav_name = f"RESPONSE_{uid}.wav"
        wav_path = os.path.join(blend_file_path, wav_name)
        
        if os.path.exists(wav_path):
            try:
                new_sound = se.sequences.new_sound(
                    name=wav_name,
                    filepath=wav_path,
                    channel=RESPONSE_CHANNEL, # Channel 1
                    frame_start=int(current_write_head)
                )
                new_response_strips.append(new_sound)
                current_write_head += new_sound.frame_final_duration
            except Exception as e:
                print(f"Error inserting {wav_name}: {e}")

    # -------------------------------------------------------------------------
    # STEP 5: THE FINAL AUDIT (Post-Processing Alignment)
    # -------------------------------------------------------------------------
    # This runs after everything is settled to fix any "gravity" slips.
    
    print("Running Final Channel Audit...")
    
    # 1. Force Original Clips
    for r in valid_ranges:
        for item in range_groups[r['id']]:
            s = item['strip']
            target = item['chan']
            
            if s.channel != target:
                print(f"Correction: Moving {s.name} from {s.channel} back to {target}")
                s.channel = target

    # 2. Force Response Clips
    for s in new_response_strips:
        if s.channel != RESPONSE_CHANNEL:
             s.channel = RESPONSE_CHANNEL

    # Reset Timeline
    scene.frame_current = 1
    print("DONE. Channels Enforced.")

if __name__ == "__main__":
    main()