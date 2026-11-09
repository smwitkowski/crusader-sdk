-- crusader-bridge: lets the bridge stop the game on an exact tick.
--
-- Crusader 1.41 (exe sha256 3bb0a8c1...) runs one game tick per call of the function at 0x0045CE16.
-- Before each tick it skips the tick if the pause flag is set; at 0x0045CE58 it increments the tick
-- counter (`add dword [0x01FE7DA8], 1`, 7 bytes). We replace that instruction with a jump to a stub
-- that does the increment. A separate hook sets the pause flag once tick >= target.
-- The bridge writes `target` (address logged at startup) to run N ticks.
-- Addresses from OpenSHC (GameCore at 0x01FE7D10: mapTimeInTicks +0x98, gamePausedLogical +0x2344).

local TICK = 0x01FE7DA8
local PAUSED = 0x01FEA054
local HOOK = 0x0045CE58  -- add dword [TICK], 1
local RESUME = HOOK + 7
local FRAME_HOOK = 0x0045CE7C  -- mov ecx, 0x01A93208; runs every frame, also while paused
local FRAME_RESUME = FRAME_HOOK + 5
local PARAMS = 0x01997FB8  -- GameSynchronyState command parameters 0..5
local SYNC_STATE = 0x0191D768  -- DAT_GameSynchronyState
local QUEUE_COMMAND = 0x00489100  -- GameSynchronyState::queueCommand(GameCommandType)
local RNG = 0x01A279C0  -- Random::RNG instance: seed at +4

local function le32(v)
  v = v % 0x100000000
  return {v % 256, (v // 256) % 256, (v // 65536) % 256, v // 16777216}
end

local function bytes(...)
  local out = {}
  for _, part in ipairs({...}) do
    if type(part) == "table" then
      for _, b in ipairs(part) do out[#out + 1] = b end
    else
      out[#out + 1] = part
    end
  end
  return out
end

return {
  enable = function(self, config)
    local target = core.allocate(4)
    core.writeInteger(target, 0)  -- 0: the match pauses on its first tick until the bridge advances it
    -- Pending RNG seed: when the bridge writes a non-zero seed here (before loading a save), the next
    -- tick re-seeds the game's RNG with it (RNG.seed = seed; populateRNG1040 0x0046A760: srand + refill
    -- the 20000-entry table + reset indices, as a multiplayer start does at 0x4418CF) before that tick's
    -- simulation runs, so the first tick after a load is already seeded.
    local seed_slot = core.allocate(4)
    core.writeInteger(seed_slot, 0)
    local stub = core.allocateCode(96)
    local code = bytes(
      0x83, 0x05, le32(TICK), 0x01,             -- add dword [TICK], 1   (the instruction we replaced)
      0x50,                                     -- push eax
      0xA1, le32(seed_slot),                    -- mov eax, [seed_slot]
      0x85, 0xC0,                               -- test eax, eax
      0x74, 27,                                 -- jz +27 (no pending seed)
      0xA3, le32(RNG + 4),                      -- mov [RNG.seed], eax
      0x60,                                     -- pushad
      0xB9, le32(RNG))                          -- mov ecx, RNG
    code = bytes(code, 0xE8, le32(0x0046A760 - (stub + #code + 5)))  -- call RNG::populateRNG1040
    code = bytes(code,
      0x61,                                     -- popad
      0xC7, 0x05, le32(seed_slot), le32(0),     -- mov dword [seed_slot], 0
      0x58)                                     -- pop eax
    local jmp_back = #code + 5
    code = bytes(code, 0xE9, le32(RESUME - (stub + jmp_back)))  -- jmp RESUME
    core.writeCode(stub, code)
    core.writeCode(HOOK, bytes(0xE9, le32(stub - (HOOK + 5)), 0x90, 0x90))  -- jmp stub; nop; nop

    -- Pause point. The pause must not be set inside a tick: the game skips the second half of a tick's
    -- simulation (updateBuildings, updateTrees, units... from 0x45CF56) when it finds the pause flag set
    -- at 0x45CF01, so a pause set at the tick increment cut every advance's last tick short. Instead, at
    -- the start of the next tick decision (0x45CE24: cmp dword [PAUSED], 0) we pause once tick >= target.
    -- The same stub also unpauses (tick < target): the bridge only writes the target. A frame reads the pause flag
    -- three times (the decision, the mailbox stub's early return, 0x45CF01), and an unpause written by the bridge at an
    -- arbitrary moment could land after the decision had skipped the tick, so that frame ran the map upkeep and the
    -- second half of a tick with no tick (idle skirmish runs could diverge). Set here,
    -- the flag is the same for the whole frame. It also pauses once the game has ended a skirmish
    -- (MapAndTimeState.gameOver 0x0117D500, set a little after a lord dies; the end screen that follows stops the
    -- ticks), so a run ends on the first tick decision after the match ended. Castle Builder never sets it.
    local DECIDE = 0x0045CE24  -- cmp dword [0x01FEA054], 0 (7 bytes)
    local GAME_OVER = 0x0117D500
    local pstub = core.allocateCode(64)
    local pcode = bytes(
      0x50,                                     -- push eax
      0xA1, le32(TICK),                         -- mov eax, [TICK]
      0x3B, 0x05, le32(target),                 -- cmp eax, [target]
      0x7D, 21,                                 -- jge +21 (pause)
      0x83, 0x3D, le32(GAME_OVER), 0x00,        -- cmp dword [GAME_OVER], 0
      0x75, 12,                                 -- jne +12 (pause)
      0xC7, 0x05, le32(PAUSED), le32(0),        -- mov dword [PAUSED], 0 (run this frame's tick)
      0xEB, 10,                                 -- jmp +10
      0xC7, 0x05, le32(PAUSED), le32(1),        -- pause: mov dword [PAUSED], 1
      0x58,                                     -- pop eax
      0x83, 0x3D, le32(PAUSED), 0x00)           -- cmp dword [PAUSED], 0 (the instruction we replaced)
    pcode = bytes(pcode, 0xE9, le32((DECIDE + 7) - (pstub + #pcode + 5)))
    core.writeCode(pstub, pcode)
    core.writeCode(DECIDE, bytes(0xE9, le32(pstub - (DECIDE + 5)), 0x90, 0x90))
    log(INFO, string.format("[crusader-bridge]: tick hook installed; advance target at 0x%X", target))
    log(INFO, string.format("[crusader-bridge]: rng seed slot at 0x%X", seed_slot))

    -- One tick per frame. The main loop (0x0057C31A) asks how many ticks are due this frame (0x487A30),
    -- stores it at 0x01FE7DC0 and runs that many command+tick iterations back to back; per-frame work
    -- only runs between frames. At high game speed the batch size depends on wall-clock time, so the
    -- same commands gave different games (RNG draw counts split around tick 820). Capping the batch at
    -- one tick makes every tick see the same per-frame work; single-stepped runs matched exactly. It is
    -- set to exactly one (never zero), so frames with no tick due cannot add per-frame work between ticks.
    local TICKS_DUE_STORE = 0x0057C33C  -- mov [0x01FE7DC0], eax (A3 imm32, 5 bytes)
    local cap = core.allocateCode(32)
    local ccode = bytes(
      0xB8, le32(1),                            -- mov eax, 1 (exactly one tick due, never zero)
      0xA3, le32(0x01FE7DC0))                   -- mov [ticksDue], eax (the instruction we replaced)
    ccode = bytes(ccode, 0xE9, le32((TICKS_DUE_STORE + 5) - (cap + #ccode + 5)))
    core.writeCode(cap, ccode)
    core.writeCode(TICKS_DUE_STORE, bytes(0xE9, le32(cap - (TICKS_DUE_STORE + 5))))

    -- Draw only every Nth running in-match frame. The main loop draws the town and UI after the frame's tick
    -- (0x57C3EE..0x57C6D7, entered when [0xF983FC] == 0, ebx = 0) in software, which costs most of a frame;
    -- the bridge reads game memory, not pixels. Running in-match frames skip that block except every Nth
    -- (draw_every defaults to 1000; 1 draws every frame).
    -- A paused match draws its first 3 frames after each pause (so a screenshot shows the tick it stopped on)
    -- and then stops redrawing the same picture while the bridge works, sleeping 1 ms a frame instead of
    -- spinning (so a paused game leaves the CPU to its bridge and to other games); menus always draw.
    local DRAW = 0x0057C3EE  -- cmp [0x00F983FC], ebx (6 bytes)
    local MENU_VIEW = 0x01FE7D1C
    local draw_every = core.allocate(4)
    core.writeInteger(draw_every, 1000)
    local countdown = core.allocate(4)
    core.writeInteger(countdown, 0)
    local paused_left = core.allocate(4)
    core.writeInteger(paused_left, 3)
    local drawn = core.allocate(4)  -- running in-match frames drawn (smoke checks)
    core.writeInteger(drawn, 0)
    local wstub = core.allocateCode(128)
    local wcode = bytes(
      0x83, 0x3D, le32(PAUSED), 0x00,           --  0 cmp dword [PAUSED], 0
      0x75, 61,                                 --  7 jne paused
      0x83, 0x3D, le32(MENU_VIEW), 0x0E,        --  9 cmp dword [menu view], 14 (in a match)
      0x75, 36,                                 -- 16 jne draw
      0xC7, 0x05, le32(paused_left), le32(3),   -- 18 mov dword [paused_left], 3
      0xFF, 0x0D, le32(countdown),              -- 28 dec dword [countdown]
      0x7F, 29,                                 -- 34 jg skip
      0x50,                                     -- 36 push eax
      0xA1, le32(draw_every),                   -- 37 mov eax, [draw_every]
      0xA3, le32(countdown),                    -- 42 mov [countdown], eax
      0x58,                                     -- 47 pop eax
      0xFF, 0x05, le32(drawn),                  -- 48 inc dword [drawn]
      0x39, 0x1D, le32(0x00F983FC))             -- 54 draw: cmp [0xF983FC], ebx (the instruction we replaced)
    wcode = bytes(wcode, 0xE9, le32((DRAW + 6) - (wstub + #wcode + 5)))  -- 60 jmp back
    wcode = bytes(wcode, 0xE9, le32(0x0057C6D7 - (wstub + #wcode + 5)))  -- 65 skip: jmp past the draw block
    wcode = bytes(wcode,
      0x83, 0x3D, le32(MENU_VIEW), 0x0E,        -- 70 paused: cmp dword [menu view], 14
      0x75, 0xE7,                               -- 77 jne draw (-25)
      0x83, 0x3D, le32(draw_every), 0x01,       -- 79 cmp dword [draw_every], 1
      0x7E, 0xDE,                               -- 86 jle draw (-34)
      0x83, 0x3D, le32(paused_left), 0x00,      -- 88 cmp dword [paused_left], 0
      0x7E, 8,                                  -- 95 jle idle
      0xFF, 0x0D, le32(paused_left),            -- 97 dec dword [paused_left]
      0xEB, 0xCD,                               -- 103 jmp draw (-51)
      0x50, 0x51, 0x52,                         -- 105 idle: push eax/ecx/edx
      0x6A, 0x01,                               -- 108 push 1
      0xFF, 0x15, le32(0x0059E14C),             -- 110 call [KERNEL32.Sleep] (stdcall)
      0x5A, 0x59, 0x58,                         -- 116 pop edx/ecx/eax
      0xEB, 0xC8)                               -- 119 jmp skip (-56)
    core.writeCode(wstub, wcode)
    core.writeCode(DRAW, bytes(0xE9, le32(wstub - (DRAW + 5)), 0x90))
    log(INFO, string.format("[crusader-bridge]: drawn frames at 0x%X", drawn))
    log(INFO, string.format("[crusader-bridge]: draw every at 0x%X", draw_every))

    -- Command mailbox: {commandType, p0..p5}. Every frame (paused or not) the code at FRAME_HOOK runs;
    -- if commandType is set we copy p0..p5 into the game's command parameter slots and call the game's
    -- own GameSynchronyState::queueCommand(commandType), exactly as its UI does, then clear the mailbox.
    -- The bridge writes p0..p5 first and commandType last.
    local mailbox = core.allocate(28)
    for i = 0, 6 do core.writeInteger(mailbox + 4 * i, 0) end
    local fstub = core.allocateCode(640)
    local fcode = bytes(
      0x60,                                     -- pushad
      0xA1, le32(mailbox),                      -- mov eax, [mailbox]
      0x85, 0xC0,                               -- test eax, eax
      0x0F, 0x84, 0, 0, 0, 0)                   -- jz done (patched below)
    local jz_end = #fcode
    for i = 0, 5 do
      fcode = bytes(fcode,
        0x8B, 0x0D, le32(mailbox + 4 + 4 * i),  -- mov ecx, [mailbox + 4 + 4i]
        0x89, 0x0D, le32(PARAMS + 4 * i))       -- mov [PARAMS + 4i], ecx
    end
    local function call(target)                 -- call rel32 at the current end of fcode
      return bytes(0xE8, le32(target - (fstub + #fcode + 5)))
    end
    -- GCT_UNITS_SELECT (16): like the UI (UnitsState::createTribeFromSelectedUnits 0x535B00), take a free tribe id
    -- for the local player (TribesState::getAvailableTribeID 0x522720, thiscall on 0x01667F78, which marks it used)
    -- into p0 and TribesState's current tribe, and leave it in `tribe` for the bridge's move/attack orders. The
    -- bridge has already written the selection bitset (UnitsState+0x74), which queueCommand snapshots.
    local tribe = core.allocate(4)
    core.writeInteger(tribe, 0)
    fcode = bytes(fcode,
      0x83, 0xF8, 0x10,                         -- cmp eax, 16
      0x75, 33,                                 -- jne +33
      0x50,                                     -- push eax
      0xFF, 0x35, le32(0x01A275DC),             -- push dword [localPlayer]
      0xB9, le32(0x01667F78))                   -- mov ecx, TribesState
    fcode = bytes(fcode, call(0x00522720))      -- call getAvailableTribeID (ret 4)
    fcode = bytes(fcode,
      0xA3, le32(PARAMS),                       -- mov [PARAMS], eax
      0xA3, le32(0x01667F78),                   -- mov [TribesState.currentTribe], eax
      0xA3, le32(tribe),                        -- mov [tribe], eax
      0x58)                                     -- pop eax
    log(INFO, string.format("[crusader-bridge]: selected tribe at 0x%X", tribe))
    -- GCT_SAVE (39): like the game's save dialog (0x4947C3), p0 = current tick and p1 = the unit hash
    -- GameSynchronyState::computeSomeHashOnUnitArray (0x0047EEB0); the bridge writes the file name into
    -- GameSynchronyState.shortMapName and p2 itself.
    fcode = bytes(fcode,
      0x83, 0xF8, 0x27,                         -- cmp eax, 39
      0x75, 29,                                 -- jne +29 (past the hash call)
      0x8B, 0x0D, le32(TICK),                   -- mov ecx, [TICK]
      0x89, 0x0D, le32(PARAMS),                 -- mov [PARAMS], ecx
      0x50,                                     -- push eax
      0xB9, le32(SYNC_STATE))                   -- mov ecx, GameSynchronyState
    fcode = bytes(fcode, call(0x0047EEB0))      -- call computeSomeHashOnUnitArray
    fcode = bytes(fcode,
      0xA3, le32(PARAMS + 4),                   -- mov [PARAMS + 4], eax
      0x58)                                     -- pop eax
    -- Bridge probe 0x7F000002 (not a game command): the game's own building placement check, as placeBuilding (0x5162D0)
    -- runs it before it places anything: TileMapState::checkPlacement 0x5037B0 (thiscall on 0x01A93208; player, x, y,
    -- mapper, size; ret 0x14) with p0..p3 = x, y, mapper, size. It leaves refused (TileMapState +0x554934, nonzero =
    -- the game drops the build) and the reason code (+0x554938, the index of the UI's message in cr.tex group 77; 0 = none
    -- given) in `place`; nothing is queued.
    -- It also leaves the game's own MapPropertiesState::isMapperAvailable (0x4BB010, thiscall on 0x01653858; mapper;
    -- ret 4) in place + 8: 0 when this map's build menu does not offer the building (the only check of it is in the UI;
    -- the PLACE_BUILDING executor places hidden buildings, G1 S2).
    local place = core.allocate(12)
    core.writeInteger(place, 0)
    core.writeInteger(place + 4, 0)
    core.writeInteger(place + 8, 0)
    fcode = bytes(fcode,
      0x3D, le32(0x7F000002),                   -- cmp eax, 0x7F000002
      0x75, 96,                                 -- jne +96 (not this probe)
      0xC7, 0x05, le32(0x01A93208 + 0x554938), le32(0),  -- mov dword [reason], 0 (the check sets it only on some paths)
      0xFF, 0x35, le32(mailbox + 16),           -- push dword [p3] size
      0xFF, 0x35, le32(mailbox + 12),           -- push dword [p2] mapper
      0xFF, 0x35, le32(mailbox + 8),            -- push dword [p1] y
      0xFF, 0x35, le32(mailbox + 4),            -- push dword [p0] x
      0xFF, 0x35, le32(0x01A275DC),             -- push dword [localPlayer]
      0xB9, le32(0x01A93208))                   -- mov ecx, TileMapState
    fcode = bytes(fcode, call(0x005037B0))      -- call checkPlacement
    fcode = bytes(fcode,
      0xA1, le32(0x01A93208 + 0x554934),        -- mov eax, [refused]
      0xA3, le32(place),                        -- mov [place], eax
      0xA1, le32(0x01A93208 + 0x554938),        -- mov eax, [reason]
      0xA3, le32(place + 4),                    -- mov [place + 4], eax
      0xFF, 0x35, le32(mailbox + 12),           -- push dword [p2] mapper
      0xB9, le32(0x01653858))                   -- mov ecx, MapPropertiesState
    fcode = bytes(fcode, call(0x004BB010))      -- call isMapperAvailable
    fcode = bytes(fcode,
      0xA3, le32(place + 8),                    -- mov [place + 8], eax
      0xE9, 0, 0, 0, 0)                         -- jmp past queueCommand (patched below)
    local place_jmp = #fcode
    -- Bridge op 0x7F000003 (not a game command): an in-frame write (p0 = address, p1 = value, p2 = size 1, 2 or 4), for
    -- state the game's UI handlers write directly instead of queueing a command. It runs here, at the mailbox point of a
    -- frame, like a UI handler would, never as a host write in the middle of a frame (determinism fix #5).
    fcode = bytes(fcode,
      0x3D, le32(0x7F000003),                   -- cmp eax, 0x7F000003
      0x75, 45,                                 -- jne +45 (not this op)
      0xA1, le32(mailbox + 4),                  -- mov eax, [p0] address
      0x8B, 0x0D, le32(mailbox + 8),            -- mov ecx, [p1] value
      0x83, 0x3D, le32(mailbox + 12), 0x01,     -- cmp dword [p2], 1
      0x75, 4,                                  -- jne +4
      0x88, 0x08,                               -- mov [eax], cl
      0xEB, 16,                                 -- jmp end
      0x83, 0x3D, le32(mailbox + 12), 0x02,     -- cmp dword [p2], 2
      0x75, 5,                                  -- jne +5
      0x66, 0x89, 0x08,                         -- mov [eax], cx
      0xEB, 2,                                  -- jmp end
      0x89, 0x08,                               -- mov [eax], ecx
      0xE9, 0, 0, 0, 0)                         -- end: jmp past queueCommand (patched below)
    local write_jmp = #fcode
    -- Bridge op 0x7F000004 (not a game command): call a game function the way a UI handler does, at the mailbox point
    -- of a frame: p0 = its address, p1 = this (ecx), p2..p5 = up to 4 stack arguments (p2 first); eax is left in `gcall`.
    -- esp is put back from esi afterwards, so callee-cleanup and cdecl functions of any arity both work. The bridge uses it
    -- for the UI's own checks and prices (repair cost 0x410320, enemy-near 0x4A15B0, decoration height 0x4FFBA0).
    local gcall = core.allocate(4)
    core.writeInteger(gcall, 0)
    fcode = bytes(fcode,
      0x3D, le32(0x7F000004),                   -- cmp eax, 0x7F000004
      0x75, 50,                                 -- jne +50 (not this op)
      0x89, 0xE6,                               -- mov esi, esp
      0xFF, 0x35, le32(mailbox + 24),           -- push dword [p5]
      0xFF, 0x35, le32(mailbox + 20),           -- push dword [p4]
      0xFF, 0x35, le32(mailbox + 16),           -- push dword [p3]
      0xFF, 0x35, le32(mailbox + 12),           -- push dword [p2]
      0x8B, 0x0D, le32(mailbox + 8),            -- mov ecx, [p1]
      0xFF, 0x15, le32(mailbox + 4),            -- call dword [p0]
      0x89, 0xF4,                               -- mov esp, esi
      0xA3, le32(gcall),                        -- mov [gcall], eax
      0xE9, 0, 0, 0, 0)                         -- jmp past queueCommand (patched below)
    local call_jmp = #fcode
    fcode = bytes(fcode,
      0x50,                                     -- push eax (commandType)
      0xB9, le32(SYNC_STATE))                   -- mov ecx, GameSynchronyState
    fcode = bytes(fcode, call(QUEUE_COMMAND))   -- call queueCommand (thiscall, pops its arg)
    local rel3 = le32(#fcode - place_jmp)       -- the placement probe jumps to the mailbox clear below
    for i = 1, 4 do fcode[place_jmp - 4 + i] = rel3[i] end
    local rel4 = le32(#fcode - write_jmp)       -- the write op jumps there too
    for i = 1, 4 do fcode[write_jmp - 4 + i] = rel4[i] end
    local rel5 = le32(#fcode - call_jmp)        -- and the game-call op
    for i = 1, 4 do fcode[call_jmp - 4 + i] = rel5[i] end
    fcode = bytes(fcode, 0xC7, 0x05, le32(mailbox), le32(0))  -- mov dword [mailbox], 0
    local rel = le32(#fcode - jz_end)
    for i = 1, 4 do fcode[jz_end - 4 + i] = rel[i] end
    fcode = bytes(fcode,
      0x61,                                     -- done: popad
      -- Paused frames stop here: the map and pathfinding upkeep after FRAME_HOOK (separate-area map,
      -- path linkage, tile layers) is incremental, so running it on paused frames made the game depend
      -- on how long the bridge stayed paused. Return the way the game's own paused path does (0x45CDA8).
      0x83, 0x3D, le32(PAUSED), 0x00,           -- cmp dword [PAUSED], 0
      0x0F, 0x85, 0, 0, 0, 0)                   -- jne 0x45CDA8 (patched below)
    local jne_end = #fcode
    local rel2 = le32(0x0045CDA8 - (fstub + jne_end))
    for i = 1, 4 do fcode[jne_end - 4 + i] = rel2[i] end
    fcode = bytes(fcode,
      0xB9, le32(0x01A93208))                   -- mov ecx, 0x01A93208 (the instruction we replaced)
    fcode = bytes(fcode, 0xE9, le32(FRAME_RESUME - (fstub + #fcode + 5)))
    core.writeCode(fstub, fcode)
    core.writeCode(FRAME_HOOK, bytes(0xE9, le32(fstub - (FRAME_HOOK + 5))))
    log(INFO, string.format("[crusader-bridge]: command mailbox at 0x%X", mailbox))
    log(INFO, string.format("[crusader-bridge]: placement check at 0x%X", place))
    log(INFO, string.format("[crusader-bridge]: game call at 0x%X", gcall))

    -- UI-tap recorder: every call of GameSynchronyState::queueCommand (0x00489100; from the UI, the AI or the mailbox) is
    -- copied into a ring of 64 entries of 8 ints {type, p0..p5, return address} at taps + 32 + 32 * (n % 64), where
    -- n = [taps] counts every call so far. The caller's return address tells the UI's queue site from the mailbox's. The
    -- hook only reads game state, so no game result changes. queueCommand starts push ebx; push esi; mov esi, ecx;
    -- mov eax, [esi+0x109EE0] (10 bytes), replayed after the copy.
    local taps = core.allocate(32 + 64 * 32)
    for i = 0, (32 + 64 * 32) / 4 - 1 do core.writeInteger(taps + 4 * i, 0) end
    local qstub = core.allocateCode(160)
    local qcode = bytes(
      0x60,                                     -- pushad: ret at [esp+0x20], type at [esp+0x24]
      0xA1, le32(taps),                         -- mov eax, [taps]
      0x83, 0xE0, 0x3F,                         -- and eax, 63
      0xC1, 0xE0, 0x05,                         -- shl eax, 5
      0x05, le32(taps + 32),                    -- add eax, taps + 32
      0x8B, 0x4C, 0x24, 0x24,                   -- mov ecx, [esp+0x24] type
      0x89, 0x08)                               -- mov [eax], ecx
    for i = 0, 5 do
      qcode = bytes(qcode,
        0x8B, 0x0D, le32(PARAMS + 4 * i),       -- mov ecx, [PARAMS + 4i]
        0x89, 0x48, 4 + 4 * i)                  -- mov [eax + 4 + 4i], ecx
    end
    qcode = bytes(qcode,
      0x8B, 0x4C, 0x24, 0x20,                   -- mov ecx, [esp+0x20] return address
      0x89, 0x48, 0x1C,                         -- mov [eax + 28], ecx
      0xFF, 0x05, le32(taps),                   -- inc dword [taps]
      0x61,                                     -- popad
      0x53, 0x56, 0x8B, 0xF1,                   -- push ebx; push esi; mov esi, ecx (the replaced instructions)
      0x8B, 0x86, le32(0x109EE0))               -- mov eax, [esi+0x109EE0]
    qcode = bytes(qcode, 0xE9, le32((QUEUE_COMMAND + 10) - (qstub + #qcode + 5)))
    core.writeCode(qstub, qcode)
    core.writeCode(QUEUE_COMMAND, bytes(0xE9, le32(qstub - (QUEUE_COMMAND + 5)), 0x90, 0x90, 0x90, 0x90, 0x90))
    log(INFO, string.format("[crusader-bridge]: ui tap at 0x%X", taps))

  end,
  disable = function(self, config) end,
}
