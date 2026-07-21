# Provide accessible authentication methods

> Authentication flows avoid unnecessary cognitive tests and support assistive mechanisms such as password managers, paste, OTP autofill, and passkeys.

**Priority:** high · **Difficulty:** advanced · **Time:** 25 min

---
Authentication should not depend on the user's ability to memorize, transcribe, or manually reproduce information when an assistive path is feasible. Good accessible authentication usually improves security too, because it works with password managers, device-based verification, and passkeys rather than against them.

## Code Example

```html
<!-- Better: password-manager and OTP-friendly fields -->
<label for="email">Email</label>
<input id="email" name="email" type="email" autocomplete="username webauthn">

<label for="password">Password</label>
<input
  id="password"
  name="password"
  type="password"
  autocomplete="current-password">

<label for="otp">Verification code</label>
<input
  id="otp"
  name="otp"
  inputmode="numeric"
  autocomplete="one-time-code">
```

```tsx
function VerifyCodeField({
  onSubmit,
}: {
  onSubmit: (code: string) => void
}) {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        const formData = new FormData(event.currentTarget)
        onSubmit(String(formData.get('otp') ?? ''))
      }}
    >
      <label htmlFor="otp">Enter the verification code</label>
      <input
        autoComplete="one-time-code"
        id="otp"
        inputMode="numeric"
        name="otp"
        type="text"
      />

      <button type="submit">Continue</button>
    </form>
  )
}
```

```html
<!-- Better: offer a non-memory-dependent alternative -->
<button type="button">Continue with a passkey</button>
<button type="button">Email me a sign-in link</button>
```

## Why It Matters

Many authentication patterns are built around unnecessary friction: blocked paste, custom OTP widgets that break autofill, CAPTCHA transcription, or backup questions that require memory instead of possession-based proof.

- cognitive barriers prevent account access before the user can do anything else
- password-manager hostility leads to weaker, reused passwords
- speech, switch, and keyboard-only users face more effort when copy/paste and autofill are disabled
- recovery and MFA steps often fail even when the main login form looks acceptable

## Best Practices

### Support assisted entry

Authentication should work with:

- password managers
- pasted credentials and codes
- OS/browser OTP autofill
- passkeys or device approval when available

Do not split a one-time code into a widget that breaks standard autofill unless you have verified the real browser behavior.

### Provide a non-memory-dependent path

At least one viable route through sign-in, MFA, and recovery should avoid a cognitive function test. Good examples include:

- passkeys
- approval on a trusted device
- magic links
- password-manager-assisted password entry

### Keep anti-abuse controls proportional

If you use CAPTCHA or other abuse mitigations in auth flows, provide an alternative path that does not force memorization or transcription. Accessibility and abuse prevention must be designed together, not as competing concerns.

## Standards

- This rule maps to WCAG 2.2 Success Criterion 3.3.8 Accessible Authentication (Minimum).
- The practical goal is not "less security"; it is at least one viable path that does not depend on a cognitive function test.

## Exceptions

- Re-entering a newly created password can be a valid security exception when the system does not reveal the password back to the user.
- MFA is compatible with this rule, but the user still needs at least one practical path that does not rely on memorizing or transcribing information.
- Accessibility does not require removing security; it requires choosing security controls that users can actually complete.

## Verification

### Automated Checks

- Search auth flows for blocked paste handlers, OTP widgets, and missing autocomplete attributes.
- Verify username, current-password, new-password, and one-time-code fields use appropriate semantics.

### Manual Checks

- Test sign-in with a password manager.
- Paste an OTP or let the browser autofill it where supported.
- Exercise recovery and MFA flows, not only the primary login form.
- Fail if the only available path requires memorizing, transcribing, or solving a cognitive test without an assisted alternative.