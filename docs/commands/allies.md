# Allies commands

These commands are the game's "talk to allies" panel: giving an allied computer lord orders, sending and requesting goods, and answering his requests. They apply only to players allied with the controlled player. The bridge's built-in match types (a skirmish against one computer lord, Castle Builder, a loaded save) start with no allies, so there every call is refused with `player N is not your ally; allies: []` and `state()` has no `allies` key. With allies present, `state()["allies"]` lists them, their lords, and per ally the pending `request` and current `order`.

Shared rules: `ally` is the allied player's number and his lord must be alive (`your ally (player N) has no lord left`). Goods quantities are positive multiples of 5. Commands are queued for when time next moves and are refused after the match has ended or a tick budget is spent.

## `ally_order`

Ask an ally to attack an enemy, defend the player's castle, or drop his orders. [API reference](../api.md#ally_order).

- **Arguments:** `order` is `attack`, `defend` or `cancel`. `attack` needs `target`, the player number of an enemy whose lord is alive; the other orders must not pass a target.
- **Effect:** the ally decides when time next moves. A computer ally agrees only when his army is strong enough. If he agrees, his entry in `state()["allies"]["panel"]` shows `order` as `{"attack": player}` or `"defend"`; otherwise it stays `None`.
- **Refused when:** the player is not an ally or has no lord; `order` is not one of the three; an attack target is not an enemy with a living lord; or a target is given with `defend` or `cancel`.

```python
game.ally_order(2, "attack", target=3)
# {"queued": "ally_order", "ally": 2, "order": "attack", "target": 3, "note": "..."}
```

See also: [state reference](../reference/state.md#allies); [refusals](../reference/errors.md#ally_order).


## `ally_send_goods`

Give goods or gold to an ally. [API reference](../api.md#ally_send_goods).

- **Arguments:** `good` is any good name including `gold`; `qty` is a positive multiple of 5.
- **Effect:** the goods leave the player's stock and enter the ally's when time next moves. For goods other than gold the ally needs a store with room, and only as much as fits is sent: the result's `qty` is the amount actually queued.
- **Refused when:** the player holds less than `qty`; the ally has no store for the good, or no room in it; or `qty` is not a positive multiple of 5.

```python
game.ally_send_goods(2, "wood", 25)
# {"queued": "ally_send_goods", "ally": 2, "good": "wood", "qty": 25, "note": "when game time next moves"}
```

See also: [goods reference](../reference/goods.md); [refusals](../reference/errors.md#ally_send_goods).


## `ally_request_goods`

Ask an ally for goods. [API reference](../api.md#ally_request_goods).

- **Arguments:** `good` and `qty` as for `ally_send_goods`.
- **Effect:** the ally decides at once. He never gives gold and keeps a reserve of each good, so a request beyond what he will spare is refused immediately. If he agrees the goods arrive when time next moves.
- **Needs:** room in the player's own store for the full amount.
- **Refused when:** the player has no store for the good or too little room; the ally declines (`your ally refuses to give ...`); or `qty` is not a positive multiple of 5.

```python
game.ally_request_goods(2, "stone", 10)
# {"queued": "ally_request_goods", "ally": 2, "good": "stone", "qty": 10, "note": "when game time next moves"}
```

See also: [goods reference](../reference/goods.md); [refusals](../reference/errors.md#ally_request_goods).


## `ally_answer`

Accept or refuse an ally's request for goods. [API reference](../api.md#ally_answer).

- **Arguments:** `accept` is a Boolean. The pending request is the `request` field (`{"good", "qty"}`) of the ally's entry in `state()["allies"]["panel"]`.
- **Effect:** accepting sends the requested goods exactly as `ally_send_goods` would, with the same stock and room checks; the result reports the `good` and the `qty` sent. Refusing tells the ally no. Either takes effect when time next moves.
- **Refused when:** the ally has no request outstanding, `accept` is not a Boolean, or on accepting the player lacks the goods or the ally lacks room.

```python
game.ally_answer(2, accept=False)
# {"queued": "ally_answer", "ally": 2, "accept": False, "note": "when game time next moves"}
```

See also: [state reference](../reference/state.md#allies); [refusals](../reference/errors.md#ally_answer).
