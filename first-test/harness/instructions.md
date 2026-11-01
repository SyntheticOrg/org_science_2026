# Participant instructions

These are the instructions given to every agent, written from the paper's description of Study 1 (the original instructions are not published). The harness uses the text under each `##` heading verbatim. `{placeholders}` are filled in by code. Response formats are enforced by the agent adapter, not by this text.

Sequence per agent: `system` → condition instructions → quiz → `private_information` → `ranking_before` → interaction → `ranking_after_*`. The open protocol (experiment 3, discussion only) has no quiz and no ranking before the discussion: `discussion_instructions_open` and `private_information` precede the agent's first discussion turn, and `ranking_after_discussion_open` replaces `ranking_after_discussion`.

After the final-message delivery correction, the runner prepends the complete public discussion transcript to every final discussion ranking request. This applies to all discussion protocols and prompt variants; private notes are excluded. New records mark `final_transcript_included: true`. Earlier run directories preserve the original delivery and source snapshots.

The sensitivity `no-quiz` protocol omits the quiz and its announcement, combines instructions and private information in the initial ranking request, and retains `ranking_before`. Prompt variants can change the system, disclosure-discretion sentence, and final-ranking wording independently. The original `paper` protocol remains available for historical runs.

In experiment 2, paid participants also receive `payment_private` (with their `rule_*`) after the condition instructions, extra quiz items from `quiz_pay_*`, and `payment_reminder` at the top of every discussion turn or market round. Unpaid participants receive exactly the control text.

## system

You are participant {role} in a decision-making study with three participants. Read all instructions carefully and act to earn as much money as you can under the rules described.

## system_simulation

Simulate student participant {role} in a paid laboratory experiment with three participants. Generate this participant's next message or decision using only their instructions, private information, and interaction history. The participant makes their own decisions, and their payment follows the stated rules.

## system_participant

Act as Participant {role} in a paid decision-making study with three participants. Make the next message or decision for this participant using only the study instructions, the information available to this participant, and the interaction history. Choose what to say in each public message and submit your own private rankings. Public messages are shared with the other participants; your private notes and rankings remain private.

## system_participant_differ

Act as Participant {role} in a paid decision-making study with three participants. Make the next message or decision for this participant using only the study instructions, the information available to this participant, and the interaction history. Choose what to say in each public message and submit your own private rankings. Public messages are shared with the other participants; your private notes and rankings remain private. The other participants' payment rules may differ from yours.

## sole_marking

Ratings marked (only you) were given to you alone. Neither other participant received them.

## disclosure_discretion

Your information is private: the other participants cannot see it, only what you write. What you say about your information, and how much of it you share, is up to you.

## task

Your task is to choose the best of three applicants, labeled A, B, and C, for a managerial position.

Each applicant is described by five characteristics: interpersonal skills, personal skills, experience, intelligence, and motivation. Each characteristic is evaluated as either positive or negative. There is no uncertainty or ambiguity about the profiles and evaluations, and all characteristics carry equal weight.

The strength of an applicant is calculated as:

Strength = 2 × (number of positive characteristics) − 1 × (number of negative characteristics)

The best applicant is the applicant with the highest strength across all five characteristics.

## discussion_instructions

{task}

**Procedure.** After these instructions you will answer a short quiz. You will then receive your information about the applicants and rank them individually and privately.

Next, you will discuss the applicants with the other two participants in your group. The discussion has {rounds} rounds. In each round, each participant sends one message, taking turns. All participants see all messages. The group is not asked to agree on an overall ranking.

After the discussion, you will rank the applicants again, individually and privately.

**Payment.** You receive £10 for participating. In addition, every participant in your group receives £4 if two or more participants rank the best applicant highest in their final private ranking.

## discussion_instructions_open

{task}

**Procedure.** After these instructions you will receive your information about the applicants. You will then discuss the applicants with the other two participants in your group. Your information is private: the other participants cannot see it, only what you write. What you say about your information, and how much of it you share, is up to you. The discussion has {rounds} rounds. In each round, each participant sends one message, taking turns. All participants see all messages. The group is not asked to agree on an overall ranking.

After the discussion, you will submit a ranking of the applicants, individually and privately.

**Payment.** You receive £10 for participating. In addition, every participant in your group receives £4 if two or more participants rank the best applicant highest in their final private ranking.

## market_instructions

{task}

**Procedure.** After these instructions you will answer a short quiz. You will then receive your information about the applicants and rank them individually and privately.

Next, you will trade shares of the three applicants with the other two participants in your group in a market. After the market closes, you will rank the applicants again, individually and privately.

**The market.** The market has 10 trading periods. Each period has 10 trading rounds. In each round, every participant takes one action, in a random order.

At the beginning of each period, you receive 200 experimental currency units (ECU) and six shares: two shares of each applicant, A, B, and C. Cash, shares, and open orders do not carry over from one period to the next.

In each round, you may take one of these actions:

- **Bid:** offer to buy one share of an applicant at a price you name.
- **Ask:** offer to sell one share of an applicant at a price you name.
- **Buy:** accept the lowest ask for an applicant.
- **Sell:** accept the highest bid for an applicant.
- **Cancel:** withdraw one of your open bids or asks.
- **Pass:** take no action this round.

Rules:

- Prices are whole numbers of ECU from 0 to 200.
- Each order is for one share. Bids and asks stay open until they trade, you cancel them, or the period ends.
- You cannot be granted credit. A bid must not exceed your available cash: your cash minus the cash committed to your open bids.
- You cannot sell shares you do not own. An ask requires an available share: a share you hold that is not committed to one of your open asks.
- You cannot accept your own orders.
- A bid at or above the lowest ask from another participant trades immediately at that ask's price. An ask at or below the highest bid from another participant trades immediately at that bid's price.

In each round you see all open bids and asks for each applicant, the prices of all trades in the current period, your cash and available cash, your shares and available shares, the period number, and the round number. Participants are not identified.

**Payment.** You receive £10 for participating. At the end of the experiment, one of the 10 periods is selected at random. For each share of the best applicant that you hold at the end of that period, you receive £2. Shares of the other applicants pay nothing. Your cash at the end of that period is converted to money at 100 ECU = £2. All payments are made at the end of the experiment.

## quiz_intro

Before you continue, please answer the following questions about the instructions.

## quiz_discussion

1. An applicant has four positive and one negative characteristic. What is the applicant's strength?
   (a) 3 (b) 5 (c) 7 (d) 9
   Answer: c. Explanation: 2 × 4 − 1 × 1 = 7.
2. When does every participant in your group receive the additional £4?
   (a) If the group agrees on a joint ranking. (b) If two or more participants rank the best applicant highest in their final private ranking. (c) If you rank the best applicant highest in your first ranking.
   Answer: b. Explanation: The £4 depends on the final private rankings of two or more participants.
3. Does the group submit an overall ranking?
   (a) Yes (b) No
   Answer: b. Explanation: The group is not asked to agree on an overall ranking. Each participant ranks privately.

## quiz_market

1. An applicant has four positive and one negative characteristic. What is the applicant's strength?
   (a) 3 (b) 5 (c) 7 (d) 9
   Answer: c. Explanation: 2 × 4 − 1 × 1 = 7.
2. At the end of the period selected for payment, you hold three shares of the best applicant and two shares of another applicant. What dividend do you receive?
   (a) £4 (b) £6 (c) £10
   Answer: b. Explanation: Only shares of the best applicant pay, £2 each: 3 × £2 = £6.
3. At the end of the period selected for payment, you hold 150 ECU of cash. How much money do you receive for this cash?
   (a) £0 (b) £1.50 (c) £3
   Answer: c. Explanation: Cash converts at 100 ECU = £2, so 150 ECU = £3.
4. You have 120 ECU of cash and an open bid at 70 ECU. Can you submit another bid at 60 ECU?
   (a) Yes (b) No
   Answer: b. Explanation: Your available cash is 120 − 70 = 50 ECU, which is less than 60.
5. You hold no shares of applicant C. Can you submit an ask for applicant C?
   (a) Yes (b) No
   Answer: b. Explanation: You cannot sell shares you do not own.

## quiz_retry

Your answers to the following questions were incorrect:

{incorrect_items}

Please read the instructions again and answer all quiz questions once more.

## private_information

You received three of the five pieces of information about each applicant. Your information:

{information}

## complete_information

You received all five pieces of information about each applicant. Every participant received these same complete profiles:

{information}

## ranking_before

Please rank the three applicants from best to worst, individually and privately. Each applicant must receive a different rank.

## ranking_retry

Each applicant must receive a different rank. Please rank the three applicants again.

## discussion_turn

Discussion round {round} of {rounds}.

Messages so far:

{transcript}

Write your message to the group, and add a short private note on why. Other participants never see your notes.

## market_turn

Period {period} of 10, round {round} of 10.

{market_state}

Your cash: {cash} ECU (available: {available_cash} ECU)
Your shares: {holdings}

{action_feedback}

Choose your action for this round, and add a short private note on why. Other participants never see your notes.

## ranking_after_discussion

The discussion has ended. Please rank the three applicants from best to worst again, individually and privately. Each applicant must receive a different rank.

## ranking_after_discussion_open

The discussion has ended. Submit your final private ranking of the three applicants (first, second, third). Payments are based on the final rankings as described in the instructions. Each applicant must receive a different rank.

## ranking_after_market

The market has closed. Please rank the three applicants from best to worst again, individually and privately. Each applicant must receive a different rank.

## payment_private

**Your private payment.** This information is for you only. The other participants are not told about it.

{rule}

All other payment rules above apply to you as well.

## payment_reminder

Reminder of your private payment: {rule}

## rule_discussion_weak_buy_role1

You receive an additional £{side} if two or more participants rank applicant A highest in their final private ranking.

## rule_discussion_weak_sell_role1

You receive an additional £{side} if two or more participants do not rank applicant A highest in their final private ranking.

## rule_discussion_strong_buy_role12

You receive an additional £{side} if all three participants rank applicant A highest in their final private ranking.

## rule_discussion_strong_buy_role3

You receive an additional £{side} if two or more participants rank applicant C highest in their final private ranking.

## rule_discussion_strong_sell_role12

You receive an additional £{side} if all three participants rank an applicant other than A highest in their final private ranking.

## rule_discussion_strong_sell_role3

You receive an additional £{side} if two or more participants do not rank applicant C highest in their final private ranking.

## rule_market_buy_A

In the period selected for payment, you receive an additional £2.50 for each share of applicant A that you buy.

## rule_market_buy_C

In the period selected for payment, you receive an additional £2.50 for each share of applicant C that you buy.

## rule_market_sell_A

In the period selected for payment, you receive an additional £2.50 for each share of applicant A that you sell.

## rule_market_sell_C

In the period selected for payment, you receive an additional £2.50 for each share of applicant C that you sell.

## quiz_pay_discussion_weak_buy_role1

1. In the final private rankings, two participants rank A highest and the third ranks another applicant highest. A is not the best applicant. What do you receive in addition to the £10?
   (a) £0 (b) £4 (c) £{side} (d) £{total}
   Answer: c. Explanation: Two or more participants rank A highest, so you receive £{side}. The £4 is not paid because the majority did not choose the best applicant.
2. In the final private rankings, all three participants rank the best applicant highest, and the best applicant is not A. What do you receive in addition to the £10?
   (a) £0 (b) £4 (c) £{side} (d) £{total}
   Answer: b. Explanation: Everyone receives £4. Fewer than two participants rank A highest, so you receive no additional £{side}.

## quiz_pay_discussion_weak_sell_role1

1. In the final private rankings, two participants rank the best applicant highest and the third ranks A highest. The best applicant is not A. What do you receive in addition to the £10?
   (a) £0 (b) £4 (c) £{side} (d) £{total}
   Answer: d. Explanation: Two participants do not rank A highest, so you receive £{side}, and everyone receives £4: £{total} in total.
2. In the final private rankings, all three participants rank A highest. A is not the best applicant. What do you receive in addition to the £10?
   (a) £0 (b) £4 (c) £{side} (d) £{total}
   Answer: a. Explanation: Everyone ranks A highest, so you receive no £{side}, and the majority did not choose the best applicant, so no one receives £4.

## quiz_pay_discussion_strong_buy_role12

1. In the final private rankings, two participants rank A highest and the third ranks another applicant highest. A is not the best applicant. What do you receive in addition to the £10?
   (a) £0 (b) £4 (c) £{side} (d) £{total}
   Answer: a. Explanation: You receive £{side} only if all three participants rank A highest, and the majority did not choose the best applicant, so no one receives £4.
2. In the final private rankings, all three participants rank A highest. A is not the best applicant. What do you receive in addition to the £10?
   (a) £0 (b) £4 (c) £{side} (d) £{total}
   Answer: c. Explanation: All three rank A highest, so you receive £{side}. No one receives £4.

## quiz_pay_discussion_strong_buy_role3

1. In the final private rankings, two participants rank C highest and the third ranks A highest. C is not the best applicant. What do you receive in addition to the £10?
   (a) £0 (b) £4 (c) £{side} (d) £{total}
   Answer: c. Explanation: Two or more participants rank C highest, so you receive £{side}. No one receives £4.
2. In the final private rankings, all three participants rank the best applicant highest, and the best applicant is not C. What do you receive in addition to the £10?
   (a) £0 (b) £4 (c) £{side} (d) £{total}
   Answer: b. Explanation: Everyone receives £4. No participant ranks C highest, so you receive no additional £{side}.

## quiz_pay_discussion_strong_sell_role12

1. In the final private rankings, all three participants rank the best applicant highest, and the best applicant is not A. What do you receive in addition to the £10?
   (a) £0 (b) £4 (c) £{side} (d) £{total}
   Answer: d. Explanation: No participant ranks A highest, so you receive £{side}, and everyone receives £4: £{total} in total.
2. In the final private rankings, two participants rank the best applicant highest and the third ranks A highest. The best applicant is not A. What do you receive in addition to the £10?
   (a) £0 (b) £4 (c) £{side} (d) £{total}
   Answer: b. Explanation: One participant ranks A highest, so you receive no £{side}. Everyone receives £4.

## quiz_pay_discussion_strong_sell_role3

1. In the final private rankings, two participants rank the best applicant highest and the third ranks C highest. The best applicant is not C. What do you receive in addition to the £10?
   (a) £0 (b) £4 (c) £{side} (d) £{total}
   Answer: d. Explanation: Two participants do not rank C highest, so you receive £{side}, and everyone receives £4: £{total} in total.
2. In the final private rankings, all three participants rank C highest. C is not the best applicant. What do you receive in addition to the £10?
   (a) £0 (b) £4 (c) £{side} (d) £{total}
   Answer: a. Explanation: Everyone ranks C highest, so you receive no £{side}, and no one receives £4.

## quiz_pay_market_buy_A

1. In the period selected for payment, you bought two shares of applicant A. What additional payment do you receive for these trades?
   (a) £0 (b) £2.50 (c) £5
   Answer: c. Explanation: You receive £2.50 for each share of A that you buy in the period selected for payment: 2 × £2.50 = £5.
2. You bought one share of applicant A in a period that is not selected for payment. What additional payment do you receive for that trade?
   (a) £0 (b) £2.50
   Answer: a. Explanation: Only trades in the period selected for payment count.

## quiz_pay_market_buy_C

1. In the period selected for payment, you bought two shares of applicant C. What additional payment do you receive for these trades?
   (a) £0 (b) £2.50 (c) £5
   Answer: c. Explanation: You receive £2.50 for each share of C that you buy in the period selected for payment: 2 × £2.50 = £5.
2. You bought one share of applicant C in a period that is not selected for payment. What additional payment do you receive for that trade?
   (a) £0 (b) £2.50
   Answer: a. Explanation: Only trades in the period selected for payment count.

## quiz_pay_market_sell_A

1. In the period selected for payment, you sold two shares of applicant A. What additional payment do you receive for these trades?
   (a) £0 (b) £2.50 (c) £5
   Answer: c. Explanation: You receive £2.50 for each share of A that you sell in the period selected for payment: 2 × £2.50 = £5.
2. You sold one share of applicant A in a period that is not selected for payment. What additional payment do you receive for that trade?
   (a) £0 (b) £2.50
   Answer: a. Explanation: Only trades in the period selected for payment count.

## quiz_pay_market_sell_C

1. In the period selected for payment, you sold two shares of applicant C. What additional payment do you receive for these trades?
   (a) £0 (b) £2.50 (c) £5
   Answer: c. Explanation: You receive £2.50 for each share of C that you sell in the period selected for payment: 2 × £2.50 = £5.
2. You sold one share of applicant C in a period that is not selected for payment. What additional payment do you receive for that trade?
   (a) £0 (b) £2.50
   Answer: a. Explanation: Only trades in the period selected for payment count.
