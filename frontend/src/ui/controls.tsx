import { Button as HeroButton, type ButtonProps as HeroButtonProps } from "@heroui/react";
import { mergeProps } from "@react-aria/utils";
import { forwardRef, type ComponentPropsWithoutRef } from "react";

export type CapsuleButtonProps = ComponentPropsWithoutRef<"button"> & Pick<HeroButtonProps,
  "variant" | "size" | "fullWidth" | "isIconOnly" | "isPending" | "isDisabled"
>;

/**
 * HeroUI supplies states and styling; the rendered element keeps native button
 * events and form semantics. In particular, onClick receives the real click
 * event, including the button currentTarget used by anchored interactions.
 */
export const CapsuleButton = forwardRef<HTMLButtonElement, CapsuleButtonProps>(function CapsuleButton(
  { children, className, style, type = "submit", disabled, isDisabled, isPending,
    variant = "ghost", size, fullWidth, isIconOnly, autoFocus, ...nativeProps }, ref,
) {
  const unavailable = disabled || isDisabled || false;
  return <HeroButton ref={ref} id={nativeProps.id} className={["fm-button", className].filter(Boolean).join(" ")}
    style={style} type={type} isDisabled={unavailable} isPending={isPending}
    autoFocus={autoFocus} variant={variant} size={size} fullWidth={fullWidth} isIconOnly={isIconOnly}
    onPressStart={event => event.continuePropagation()}
    onPressEnd={event => event.continuePropagation()}
    onPressUp={event => event.continuePropagation()}
    onPress={event => event.continuePropagation()}
    render={heroProps => {
      // Run app keyboard commands first, then let React Aria maintain pressed
      // state and native button activation for Enter/Space. Handled listbox
      // keys must not also activate a surrounding form.
      return <button {...mergeProps(heroProps, nativeProps)}
        children={nativeProps.dangerouslySetInnerHTML ? undefined : heroProps.children}
        onKeyDown={event => {
          nativeProps.onKeyDown?.(event);
          if (!event.defaultPrevented) heroProps.onKeyDown?.(event);
        }}
        onKeyUp={event => {
          nativeProps.onKeyUp?.(event);
          if (!event.defaultPrevented) heroProps.onKeyUp?.(event);
        }}
        onClick={event => {
          if (unavailable || isPending) { event.preventDefault(); return; }
          // Keep the caller's preventDefault / stopPropagation and currentTarget.
          nativeProps.onClick?.(event);
          heroProps.onClick?.(event);
        }} />;
    }}
  >{children}</HeroButton>;
});
