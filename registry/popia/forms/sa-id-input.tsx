"use client";

/**
 * SA ID number input.
 *
 * Only use this where a law or the core service genuinely requires an ID
 * number (FICA/KYC, payroll, tax, credit). Otherwise collect date of birth or
 * an age bracket instead (s10 minimality).
 *
 * Behaviour:
 *   - Validates format, calendar date, citizenship digit and Luhn check digit.
 *   - Shows the value masked after blur. Reveals it again on focus for editing.
 *   - Explains why the number is needed (helperText, s18(1)(c)).
 *   - Never logs the value. Disables autocomplete and spellcheck so browsers
 *     and extensions are less likely to store or send it.
 *
 * On the server: validate again, then encrypt or tokenise at field level
 * before storing (s19). Never use the number as a key or URL parameter.
 */

import * as React from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { isValidSaId, maskSaId, normaliseSaId } from "@/lib/popia/sa-id";

export interface SaIdInputProps {
  /** Controlled value (digits only). */
  value?: string;
  /** Uncontrolled initial value. */
  defaultValue?: string;
  /** Called with digits only, and whether the value is valid. */
  onChange?: (value: string, valid: boolean) => void;
  /** Why you need the number. Required: say it plainly. For example "We need your ID number to verify your identity under FICA." */
  helperText: string;
  label?: string;
  id?: string;
  name?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
  /** Error message shown for an invalid number. */
  invalidMessage?: string;
}

export function SaIdInput({
  value,
  defaultValue,
  onChange,
  helperText,
  label = "South African ID number",
  id,
  name = "sa_id_number",
  required,
  disabled,
  className,
  invalidMessage = "Check the number. A South African ID number has 13 digits.",
}: SaIdInputProps) {
  const autoId = React.useId();
  const inputId = id ?? `sa-id-${autoId}`;
  const helpId = `${inputId}-help`;
  const errorId = `${inputId}-error`;

  const isControlled = value !== undefined;
  const [inner, setInner] = React.useState(() => normaliseSaId(defaultValue ?? ""));
  const raw = isControlled ? normaliseSaId(value) : inner;

  const [focused, setFocused] = React.useState(false);
  const [touched, setTouched] = React.useState(false);

  const valid = isValidSaId(raw);
  const showError = touched && !focused && raw.length > 0 && !valid;
  const display = focused || raw.length === 0 ? raw : maskSaId(raw);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const digits = e.target.value.replace(/\D/g, "").slice(0, 13);
    if (!isControlled) setInner(digits);
    onChange?.(digits, isValidSaId(digits));
  };

  return (
    <div className={["space-y-1.5", className ?? ""].join(" ")}>
      <Label htmlFor={inputId}>
        {label}
        {required ? null : <span className="ml-1 text-muted-foreground">(optional)</span>}
      </Label>
      <Input
        id={inputId}
        type="text"
        inputMode="numeric"
        pattern="\d{13}"
        maxLength={focused ? 13 : 16}
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        data-1p-ignore
        data-lpignore="true"
        data-private="true"
        required={required}
        disabled={disabled}
        value={display}
        readOnly={!focused && raw.length > 0}
        onFocus={() => setFocused(true)}
        onBlur={() => {
          setFocused(false);
          setTouched(true);
        }}
        onChange={handleChange}
        aria-invalid={showError || undefined}
        aria-describedby={showError ? `${helpId} ${errorId}` : helpId}
      />
      {/*
        The real value is submitted through a hidden input so native form posts
        still work while the visible field is masked.
      */}
      <input type="hidden" name={name} value={raw} />
      <p id={helpId} className="text-xs text-muted-foreground">
        {helperText}
      </p>
      {showError ? (
        <p id={errorId} role="alert" className="text-xs text-destructive">
          {invalidMessage}
        </p>
      ) : null}
    </div>
  );
}
