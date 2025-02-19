import json

from pyshark.packet.layers.json_layer import JsonLayer

try:
    import ujson
    USE_UJSON = True
except ImportError:
    USE_UJSON = False

from pyshark.packet.packet import Packet


def duplicate_object_hook(ordered_pairs):
    """Make lists out of duplicate keys."""
    json_dict = {}
    for key, val in ordered_pairs:
        existing_val = json_dict.get(key)
        if not existing_val:
            json_dict[key] = val
        else:
            if isinstance(existing_val, list):
                existing_val.append(val)
            else:
                json_dict[key] = [existing_val, val]

    return json_dict


def packet_from_json_packet(json_pkt, deduplicate_fields=True):
    """Creates a Pyshark Packet from a tshark json single packet.

    Before tshark 2.6, there could be duplicate keys in a packet json, which creates the need for
    deduplication and slows it down significantly.
    """
    if deduplicate_fields:
        # NOTE: We can use ujson here for ~25% speed-up, however since we can't use hooks in ujson
        # we lose the ability to view duplicates. This might still be a good option later on.
        pkt_dict = json.loads(json_pkt.decode('utf-8'), object_pairs_hook=duplicate_object_hook)
    else:
        if USE_UJSON:
            pkt_dict = ujson.loads(json_pkt)
        else:
            pkt_dict = json.loads(json_pkt.decode('utf-8'))
    # We use the frame dict here and not the object access because it's faster.
    frame_dict = pkt_dict['_source']['layers'].pop('frame')
    layers = []
    for layer in frame_dict['frame.protocols'].split(':'):
        layer_dict = pkt_dict['_source']['layers'].pop(layer, None)
        if layer_dict is not None:
            layers.append(JsonLayer(layer, layer_dict))
    # Add all leftovers
    for name, layer in pkt_dict['_source']['layers'].items():
        layers.append(JsonLayer(name, layer))

    return Packet(layers=layers, frame_info=JsonLayer('frame', frame_dict),
                  number=int(frame_dict.get('frame.number', 0)),
                  length=int(frame_dict['frame.len']),
                  sniff_time=frame_dict['frame.time_epoch'],
                  interface_captured=frame_dict.get('frame.interface_id'))
