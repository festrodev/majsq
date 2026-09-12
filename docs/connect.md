# Connecting a Festro account

maj$q can weight its picks by a member's own Festro history. That requires
access to their account data, and the shape of that access was the single
most-reviewed decision in this project.

## What maj$q does NOT do

It never holds a Festro **user token**. A session credential is designed to
carry a person's full authority, which is exactly right for that person's own
device and exactly wrong for a third-party bot: handing one over means the bot
*is* the account, with whatever that account can do.

Revocability does not fix this. It limits the blast radius *after* someone
notices, not the authority the credential carries while it is live. So the
right shape is not "a token we can revoke quickly" but a credential that never
had the authority in the first place.

## What it does instead

A separate, opaque **connected credential**:

1. **Authorize.** The member lands on festro.com, already logged in, and sees
   exactly what they are granting. The grant is bound to this application, to
   one exact redirect URI, and to a PKCE challenge. It expires in 5 minutes.
2. **Exchange.** maj$q's server trades the code for a credential, proving its
   own client identity with its registered secret. The grant is consumed and
   the credential created in one transaction. The user must be active.
3. **Use.** The credential is accepted by exactly one endpoint,
   `GET /api/v1/connect/profile/`, which returns a *minimized* taste profile:
   weighted tags, organizers, venues, a price band, usual nights. No email, no
   reservations, no history rows, no ability to act as the member.
4. **Revoke.** Either side can drop it. Deleting a Festro account revokes it.

Ordinary Festro authentication does not recognize this credential at all. Sent
as `Authorization: Token`, it is rejected.

## The group boundary

Connecting in a DM discloses nothing in a group. Using a member's taste in a
group requires that member to opt in **there**, with a button that is as easy
to switch off as on. The setting is read on every turn before any cached
profile is consulted, so turning it off takes effect on the next message.

Reasons shown in a group are aggregate — "2 sur 3 aiment le jazz" — and never
name a member or anything they did. Only a DM, where there is one person to
talk about, gets a personal reason.

Taste consent says nothing about attendance. The poll is what says who is
coming.

## Map shares

A pick set gets an unguessable share id. The page behind it renders only public
event fields — title, time, venue, coordinates, price, the festro.com link.
Never conversation history, never a member's reasons, never a signed image URL.
