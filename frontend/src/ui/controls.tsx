import { Button as HeroButton, type ButtonProps as HeroButtonProps } from "@heroui/react";
import { mergeProps } from "@react-aria/utils";
import { forwardRef, useRef, type ComponentPropsWithoutRef, type ComponentPropsWithRef } from "react";

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
  const needsKeyboardClick = useRef(false);
  return <HeroButton ref={ref} id={nativeProps.id} className={["fm-button", className].filter(Boolean).join(" ")}
    style={style} type={type} isDisabled={unavailable} isPending={isPending}
    autoFocus={autoFocus} variant={variant} size={size} fullWidth={fullWidth} isIconOnly={isIconOnly}
    onPressStart={event => event.continuePropagation()}
    onPressEnd={event => event.continuePropagation()}
    onPressUp={event => event.continuePropagation()}
    onPress={event => {
      event.continuePropagation();
      // React Aria prevents the native keyboard click on type=button. Bridge
      // that activation back to one real DOM click, preserving currentTarget
      // for callers. Submit/reset retain their browser form activation.
      if (event.pointerType === "keyboard" && type === "button" && needsKeyboardClick.current) {
        needsKeyboardClick.current = false;
        (event.target as HTMLButtonElement).click();
      }
    }}
    render={heroProps => {
      // HeroUI's polymorphic render type covers every JSX intrinsic element.
      // This adapter always renders a native button, including its forwarded ref.
      const buttonProps = heroProps as ComponentPropsWithRef<"button">;
      // Run app keyboard commands first, then let React Aria maintain pressed
      // state and native button activation for Enter/Space. Handled listbox
      // keys must not also activate a surrounding form.
      return <button {...mergeProps(buttonProps, nativeProps)}
        children={nativeProps.dangerouslySetInnerHTML ? undefined : buttonProps.children}
        onKeyDown={event => {
          needsKeyboardClick.current = false;
          nativeProps.onKeyDown?.(event);
          if (!event.defaultPrevented) {
            buttonProps.onKeyDown?.(event);
            // macOS Enter may retain native activation; never synthesize a
            // second click unless React Aria actually prevented that default.
            needsKeyboardClick.current = (event.key === "Enter" || event.key === " ") && event.defaultPrevented;
          }
        }}
        onKeyUp={event => {
          nativeProps.onKeyUp?.(event);
          if (!event.defaultPrevented) buttonProps.onKeyUp?.(event);
          needsKeyboardClick.current = false;
        }}
        onClick={event => {
          if (unavailable || isPending) { event.preventDefault(); return; }
          // Keep the caller's preventDefault / stopPropagation and currentTarget.
          nativeProps.onClick?.(event);
          buttonProps.onClick?.(event);
        }} />;
    }}
  >{children}</HeroButton>;
});
