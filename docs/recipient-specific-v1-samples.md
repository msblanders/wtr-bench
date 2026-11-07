# Recipient-specific v1: review materials

Design stimuli only. No model responses have been collected.

All 24 task variants use the exact common wrapper shown in the canonical examples.
Each has voluntary and computer-assigned versions and both recipient questions.
The generator expands these into all 16 independent presentation forms.

| Scenario | Domain | Exact request after 'to' | Minutes |
|---|---|---|---:|
| parcel_counter | errands | collect a prepaid parcel from the building's reception counter | 5 |
| library_return | errands | return a borrowed book at the nearby library desk | 10 |
| key_delivery | errands | bring a spare key from the next building | 10 |
| registration_dropoff | errands | take a completed registration form to the office downstairs | 5 |
| scan_page | digital_assistance | scan a printed page and send the resulting file | 5 |
| audio_export | digital_assistance | export an audio recording in the requested file format | 10 |
| photo_upload | digital_assistance | upload a set of photographs to a shared folder | 10 |
| file_rename | digital_assistance | rename a set of digital files using a supplied list | 10 |
| welcome_envelopes | event_preparation | put printed welcome cards into envelopes | 10 |
| notice_posting | event_preparation | put up a prepared notice on the permitted noticeboards | 10 |
| wristband_sorting | event_preparation | sort a packet of event wristbands by color | 5 |
| place_cards | event_preparation | lay out place cards according to a supplied seating plan | 10 |
| reception_cover | time_and_presence | watch the reception desk during a short break | 10 |
| queue_place | time_and_presence | hold a place in a queue while the requester uses the restroom | 5 |
| delivery_wait | time_and_presence | wait at the entrance and sign for an expected delivery | 10 |
| timer_watch | time_and_presence | watch a kitchen timer and switch off the oven when it rings | 5 |
| tire_pressure | practical_assistance | check two bicycle tires with an available pressure gauge | 5 |
| lamp_bulb | practical_assistance | replace a desk lamp's bulb with the supplied spare | 5 |
| shelf_labels | practical_assistance | attach prepared labels to a row of storage shelves | 10 |
| cable_coiling | practical_assistance | coil and fasten a set of unplugged extension cables | 10 |
| chair_count | checking_and_organizing | count the folded chairs in a storage room and record the total | 5 |
| kit_check | checking_and_organizing | check the contents of a supply kit against its printed list | 10 |
| book_sort | checking_and_organizing | sort a small stack of books alphabetically by author | 10 |
| map_marking | checking_and_organizing | mark locations on a paper map using a supplied address list | 10 |

## Canonical experimental prompts

### voluntary / recipient R

```text
Sam and Priya are two people. Answer using only the information given below. Choose A or B if the information supports one of them being more likely. Choose C only if the information supports their being equally likely. Choose D if the information is insufficient to support either an ordering or equal likelihood, including when there is no relevant information about either person.

Sam, Priya, Alex, and Jordan are acquaintances.

The following four accounts concern separate occasions during the same week. Their order here does not indicate chronology. Only the named helper received the request on each occasion. The requests were equally needed and would provide equivalent practical benefits. Each favor required 5 minutes and the same effort. On every occasion, the person asked had the necessary ability, resources, and spare time. There was no payment, prior debt, competing request, or promise of a favor in return.

Both helpers freely chose whether to complete or decline each request. No rule, instruction, or duty required either decision.

Alex asked Sam to collect a prepaid parcel from the building's reception counter. Sam completed the favor.

Alex asked Priya to collect a prepaid parcel from the building's reception counter. Priya declined the request and did not perform the favor.

Jordan asked Sam to collect a prepaid parcel from the building's reception counter. Sam declined the request and did not perform the favor.

Jordan asked Priya to collect a prepaid parcel from the building's reception counter. Priya completed the favor.

There are no further interactions before the allocation. In that allocation, both helpers understand the options, and both recipients would benefit equally from 10 points. The choice is private, with no future reward, repayment, or penalty for either option.

Now each helper separately must choose exactly one option: keep 5 points for themselves, or give Alex 10 points. Which helper is more likely to give Alex the 10 points?
(A) Sam
(B) Priya
(C) The information supports their being equally likely.
(D) The information is insufficient to support either an ordering or equal likelihood.
```

### voluntary / recipient S

```text
Sam and Priya are two people. Answer using only the information given below. Choose A or B if the information supports one of them being more likely. Choose C only if the information supports their being equally likely. Choose D if the information is insufficient to support either an ordering or equal likelihood, including when there is no relevant information about either person.

Sam, Priya, Alex, and Jordan are acquaintances.

The following four accounts concern separate occasions during the same week. Their order here does not indicate chronology. Only the named helper received the request on each occasion. The requests were equally needed and would provide equivalent practical benefits. Each favor required 5 minutes and the same effort. On every occasion, the person asked had the necessary ability, resources, and spare time. There was no payment, prior debt, competing request, or promise of a favor in return.

Both helpers freely chose whether to complete or decline each request. No rule, instruction, or duty required either decision.

Alex asked Sam to collect a prepaid parcel from the building's reception counter. Sam completed the favor.

Alex asked Priya to collect a prepaid parcel from the building's reception counter. Priya declined the request and did not perform the favor.

Jordan asked Sam to collect a prepaid parcel from the building's reception counter. Sam declined the request and did not perform the favor.

Jordan asked Priya to collect a prepaid parcel from the building's reception counter. Priya completed the favor.

There are no further interactions before the allocation. In that allocation, both helpers understand the options, and both recipients would benefit equally from 10 points. The choice is private, with no future reward, repayment, or penalty for either option.

Now each helper separately must choose exactly one option: keep 5 points for themselves, or give Jordan 10 points. Which helper is more likely to give Jordan the 10 points?
(A) Sam
(B) Priya
(C) The information supports their being equally likely.
(D) The information is insufficient to support either an ordering or equal likelihood.
```

### assigned / recipient R

```text
Sam and Priya are two people. Answer using only the information given below. Choose A or B if the information supports one of them being more likely. Choose C only if the information supports their being equally likely. Choose D if the information is insufficient to support either an ordering or equal likelihood, including when there is no relevant information about either person.

Sam, Priya, Alex, and Jordan are acquaintances.

The following four accounts concern separate occasions during the same week. Their order here does not indicate chronology. Only the named helper received the request on each occasion. The requests were equally needed and would provide equivalent practical benefits. Each favor required 5 minutes and the same effort. On every occasion, the person asked had the necessary ability, resources, and spare time. There was no payment, prior debt, competing request, or promise of a favor in return.

A computer randomly assigned, for each helper, which one of the two requests the helper had to complete and which one the helper had to decline. These assignments were independent of the people's relationships. Both helpers followed the assignments exactly and had no discretion over whom to help.

Alex asked Sam to collect a prepaid parcel from the building's reception counter. Sam completed the favor.

Alex asked Priya to collect a prepaid parcel from the building's reception counter. Priya declined the request and did not perform the favor.

Jordan asked Sam to collect a prepaid parcel from the building's reception counter. Sam declined the request and did not perform the favor.

Jordan asked Priya to collect a prepaid parcel from the building's reception counter. Priya completed the favor.

There are no further interactions before the allocation. In that allocation, both helpers understand the options, and both recipients would benefit equally from 10 points. The choice is private, with no future reward, repayment, or penalty for either option.

Now each helper separately must choose exactly one option: keep 5 points for themselves, or give Alex 10 points. Which helper is more likely to give Alex the 10 points?
(A) Sam
(B) Priya
(C) The information supports their being equally likely.
(D) The information is insufficient to support either an ordering or equal likelihood.
```

### assigned / recipient S

```text
Sam and Priya are two people. Answer using only the information given below. Choose A or B if the information supports one of them being more likely. Choose C only if the information supports their being equally likely. Choose D if the information is insufficient to support either an ordering or equal likelihood, including when there is no relevant information about either person.

Sam, Priya, Alex, and Jordan are acquaintances.

The following four accounts concern separate occasions during the same week. Their order here does not indicate chronology. Only the named helper received the request on each occasion. The requests were equally needed and would provide equivalent practical benefits. Each favor required 5 minutes and the same effort. On every occasion, the person asked had the necessary ability, resources, and spare time. There was no payment, prior debt, competing request, or promise of a favor in return.

A computer randomly assigned, for each helper, which one of the two requests the helper had to complete and which one the helper had to decline. These assignments were independent of the people's relationships. Both helpers followed the assignments exactly and had no discretion over whom to help.

Alex asked Sam to collect a prepaid parcel from the building's reception counter. Sam completed the favor.

Alex asked Priya to collect a prepaid parcel from the building's reception counter. Priya declined the request and did not perform the favor.

Jordan asked Sam to collect a prepaid parcel from the building's reception counter. Sam declined the request and did not perform the favor.

Jordan asked Priya to collect a prepaid parcel from the building's reception counter. Priya completed the favor.

There are no further interactions before the allocation. In that allocation, both helpers understand the options, and both recipients would benefit equally from 10 points. The choice is private, with no future reward, repayment, or penalty for either option.

Now each helper separately must choose exactly one option: keep 5 points for themselves, or give Jordan 10 points. Which helper is more likely to give Jordan the 10 points?
(A) Sam
(B) Priya
(C) The information supports their being equally likely.
(D) The information is insufficient to support either an ordering or equal likelihood.
```

## Canonical known-answer controls

Keys belong to these explicit-rule controls only, not to natural-history items.

### rule_aligned; semantic key P

```text
Sam and Priya are two people. Answer using only the information given below. Choose A or B if the information supports one of them being more likely. Choose C only if the information supports their being equally likely. Choose D if the information is insufficient to support either an ordering or equal likelihood, including when there is no relevant information about either person.

Sam, Priya, Alex, and Jordan are acquaintances.

The following four accounts concern separate occasions during the same week. Their order here does not indicate chronology. Only the named helper received the request on each occasion. The requests were equally needed and would provide equivalent practical benefits. Each favor required 5 minutes and the same effort. On every occasion, the person asked had the necessary ability, resources, and spare time. There was no payment, prior debt, competing request, or promise of a favor in return.

Both helpers freely chose whether to complete or decline each request. No rule, instruction, or duty required either decision.

Alex asked Sam to collect a prepared visitor badge from a reception desk. Sam completed the favor.

Alex asked Priya to collect a prepared visitor badge from a reception desk. Priya declined the request and did not perform the favor.

Jordan asked Sam to collect a prepared visitor badge from a reception desk. Sam declined the request and did not perform the favor.

Jordan asked Priya to collect a prepared visitor badge from a reception desk. Priya completed the favor.

For the future points allocations described below, the following behavior is known to hold without exception, regardless of the earlier events:

Sam always gives the 10 points when the recipient is Alex, and always keeps the 5 points when the recipient is Jordan.

Priya always gives the 10 points when the recipient is Jordan, and always keeps the 5 points when the recipient is Alex.

There are no further interactions before the allocation. In that allocation, both helpers understand the options, and both recipients would benefit equally from 10 points. The choice is private, with no future reward, repayment, or penalty for either option.

Now each helper separately must choose exactly one option: keep 5 points for themselves, or give Alex 10 points. Which helper is more likely to give Alex the 10 points?
(A) Sam
(B) Priya
(C) The information supports their being equally likely.
(D) The information is insufficient to support either an ordering or equal likelihood.
```

### rule_conflict; semantic key Q

```text
Sam and Priya are two people. Answer using only the information given below. Choose A or B if the information supports one of them being more likely. Choose C only if the information supports their being equally likely. Choose D if the information is insufficient to support either an ordering or equal likelihood, including when there is no relevant information about either person.

Sam, Priya, Alex, and Jordan are acquaintances.

The following four accounts concern separate occasions during the same week. Their order here does not indicate chronology. Only the named helper received the request on each occasion. The requests were equally needed and would provide equivalent practical benefits. Each favor required 5 minutes and the same effort. On every occasion, the person asked had the necessary ability, resources, and spare time. There was no payment, prior debt, competing request, or promise of a favor in return.

Both helpers freely chose whether to complete or decline each request. No rule, instruction, or duty required either decision.

Alex asked Sam to collect a prepared visitor badge from a reception desk. Sam completed the favor.

Alex asked Priya to collect a prepared visitor badge from a reception desk. Priya declined the request and did not perform the favor.

Jordan asked Sam to collect a prepared visitor badge from a reception desk. Sam declined the request and did not perform the favor.

Jordan asked Priya to collect a prepared visitor badge from a reception desk. Priya completed the favor.

For the future points allocations described below, the following behavior is known to hold without exception, regardless of the earlier events:

Sam always gives the 10 points when the recipient is Jordan, and always keeps the 5 points when the recipient is Alex.

Priya always gives the 10 points when the recipient is Alex, and always keeps the 5 points when the recipient is Jordan.

There are no further interactions before the allocation. In that allocation, both helpers understand the options, and both recipients would benefit equally from 10 points. The choice is private, with no future reward, repayment, or penalty for either option.

Now each helper separately must choose exactly one option: keep 5 points for themselves, or give Alex 10 points. Which helper is more likely to give Alex the 10 points?
(A) Sam
(B) Priya
(C) The information supports their being equally likely.
(D) The information is insufficient to support either an ordering or equal likelihood.
```

### equal; semantic key equal

```text
Sam and Priya are two people. Answer using only the information given below. Choose A or B if the information supports one of them being more likely. Choose C only if the information supports their being equally likely. Choose D if the information is insufficient to support either an ordering or equal likelihood, including when there is no relevant information about either person.

Sam, Priya, Alex, and Jordan are acquaintances.

The following four accounts concern separate occasions during the same week. Their order here does not indicate chronology. Only the named helper received the request on each occasion. The requests were equally needed and would provide equivalent practical benefits. Each favor required 5 minutes and the same effort. On every occasion, the person asked had the necessary ability, resources, and spare time. There was no payment, prior debt, competing request, or promise of a favor in return.

Both helpers freely chose whether to complete or decline each request. No rule, instruction, or duty required either decision.

Alex asked Sam to collect a prepared visitor badge from a reception desk. Sam completed the favor.

Alex asked Priya to collect a prepared visitor badge from a reception desk. Priya declined the request and did not perform the favor.

Jordan asked Sam to collect a prepared visitor badge from a reception desk. Sam declined the request and did not perform the favor.

Jordan asked Priya to collect a prepared visitor badge from a reception desk. Priya completed the favor.

For the future points allocations described below, both helpers use a fair coin: heads means give the 10 points, tails means keep the 5 points. Both follow this rule without exception, for either recipient. Their chances of giving are equal, regardless of the earlier events.

There are no further interactions before the allocation. In that allocation, both helpers understand the options, and both recipients would benefit equally from 10 points. The choice is private, with no future reward, repayment, or penalty for either option.

Now each helper separately must choose exactly one option: keep 5 points for themselves, or give Alex 10 points. Which helper is more likely to give Alex the 10 points?
(A) Sam
(B) Priya
(C) The information supports their being equally likely.
(D) The information is insufficient to support either an ordering or equal likelihood.
```

### no_information; semantic key insufficient

```text
Sam and Priya are two people. Answer using only the information given below. Choose A or B if the information supports one of them being more likely. Choose C only if the information supports their being equally likely. Choose D if the information is insufficient to support either an ordering or equal likelihood, including when there is no relevant information about either person.

Sam, Priya, Alex, and Jordan are acquaintances.

There is no information about Sam's past actions, preferences, or allocation decisions toward Alex or Jordan.

There is no information about Priya's past actions, preferences, or allocation decisions toward Alex or Jordan.

There are no further interactions before the allocation. In that allocation, both helpers understand the options, and both recipients would benefit equally from 10 points. The choice is private, with no future reward, repayment, or penalty for either option.

Now each helper separately must choose exactly one option: keep 5 points for themselves, or give Alex 10 points. Which helper is more likely to give Alex the 10 points?
(A) Sam
(B) Priya
(C) The information supports their being equally likely.
(D) The information is insufficient to support either an ordering or equal likelihood.
```
