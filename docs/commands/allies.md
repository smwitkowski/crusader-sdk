# Allies commands

These commands send orders and goods to allies, request goods, and answer requests.

## `ally_order`

Ask a living ally to `"attack"`, `"defend"` or `"cancel"`. Attack requires the player ID of a living enemy lord; the other orders must omit `target`. The ally answers when time moves and may decline; inspect `state()["allies"]["panel"]` for the resulting order.

```python
game.ally_order(2, "attack", target=3)
```

See also: [API reference](../api.md#ally_order) and [refusals](../reference/errors.md#ally_order).


## `ally_send_goods`

Send a positive multiple of five to a living ally. You must have the requested amount; non-gold goods also need a suitable ally store with room. The driver caps the sent quantity to available room and returns it as `qty`. Goods move when time next moves.

```python
game.ally_send_goods(2, "wood", 25)
```

See also: [API reference](../api.md#ally_send_goods) and [refusals](../reference/errors.md#ally_send_goods).


## `ally_request_goods`

Request a positive multiple of five from a living ally. For non-gold goods your store must have room for the full amount. The ally decides immediately; it keeps a reserve and will not give gold, so a request can be refused. If accepted, goods arrive when time next moves.

```python
game.ally_request_goods(2, "wood", 25)
```

See also: [API reference](../api.md#ally_request_goods) and [refusals](../reference/errors.md#ally_request_goods).


## `ally_answer`

Answer a living ally’s outstanding goods request with a Boolean `accept`. Acceptance sends goods subject to your stock and the ally’s storage capacity; returned `qty` may be capped. Refusal tells the ally no. Either action is queued for when time next moves; no outstanding request is refused. Inspect `state()["allies"]` for requests.

```python
game.ally_answer(2, accept=False)
# {"queued": "ally_answer", "ally": 2, "accept": False,
#  "note": "when game time next moves"}
```

See also: [API reference](../api.md#ally_answer) and [refusals](../reference/errors.md#ally_answer).

