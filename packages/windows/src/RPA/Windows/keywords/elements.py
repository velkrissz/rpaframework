import inspect
from pathlib import Path
from typing import Dict, List, Optional

from RPA.core.windows.locators import Locator, WindowsElement

from RPA.Windows import utils
from RPA.Windows.keywords import ActionNotPossible, LibraryContext, keyword

if utils.IS_WINDOWS:
    import uiautomation as auto
    from uiautomation import Control


class ElementKeywords(LibraryContext):
    """Keywords for handling Control elements"""

    @keyword
    def set_anchor(
        self,
        locator: Locator,
        timeout: Optional[float] = None,
    ) -> None:
        """Set anchor to an element specified by the locator.

        All following keywords using locators will use this element
        as a root element. Specific use case could be setting
        anchor to TableControl element and then getting column data
        belonging to that TableControl element.

        To release anchor call ``Clear Anchor`` keyword.

        :param locator: string locator or Control element
        :param timeout: timeout in seconds for element lookup (default 10.0)

        Example:

        .. code-block:: robotframework

            Set Anchor  type:Table name:Orders depth:16
            FOR  ${row}  IN RANGE  200
                ${number}=  Get Value   name:number row ${row}
                Exit For Loop If   $number == ${EMPTY}
                ${sum}=  Get Value   name:sum row ${row}
                Log   Order number:${number} has sum:{sum}
            END
            Clear Anchor
        """
        self.ctx.anchor_element = self.ctx.get_element(locator, timeout=timeout)

    @keyword
    def clear_anchor(self) -> None:
        """Clears control anchor set by ``Set Anchor``

        This means that all following keywords accessing elements
        will use active window or desktop as root element.
        """
        self.ctx.anchor_element = None

    @keyword
    def print_tree(
        self,
        locator: Optional[Locator] = None,
        max_depth: int = 8,
        capture_image_folder: Optional[str] = None,
        log_as_warnings: bool = False,
        return_structure: bool = False,
    ) -> Optional[Dict[int, List[WindowsElement]]]:
        """Print a tree of control elements.

        A Windows application structure can contain multilevel element structure.
        Understanding this structure is crucial for creating locators. (based on
        controls' details and their parent-child relationship)

        This keyword can be used to output logs of application's element structure,
        starting with the element defined by the provided `locator` as root. Switch
        the `return_structure` parameter to `True` to get a tree of elements returned
        as well. (off by default to save memory)

        :param locator: The root of the tree to output.
        :param max_depth: Maximum depth level. (defaults to 8)
        :param capture_image_folder: If set, controls' images will be captured in this
            path.
        :param log_as_warnings: Enables highlighted logs (at the beginning of the log
            file as warnings) and increases visibility in the output console.
        :param return_structure: A flattened tree with all the elements collated by
            level will be returned if this is enabled.
        """
        brothers_count = {}  # cache how many brothers are in total given a child
        structure = {}  # leveled flattened tree of controls

        def GetChildren(ctrl: Control) -> Control:
            children = ctrl.GetChildren()
            children_count = len(children)
            for child in children:
                brothers_count[hash(child)] = children_count
            return children

        image_idx = 1
        target_elem = self.ctx.get_element(locator)
        root_ctrl = target_elem.item
        brothers_count[hash(root_ctrl)] = 1  # the root is always singular here
        image_folder = None
        if capture_image_folder:
            image_folder = Path(capture_image_folder).expanduser().resolve()
            image_folder.mkdir(parents=True, exist_ok=True)
        control_log = self.logger.warning if log_as_warnings else self.logger.info

        for control, depth, children_remaining in auto.WalkTree(
            root_ctrl,
            getChildren=GetChildren,
            includeTop=True,
            maxDepth=max_depth,
        ):
            control_str = str(control)
            if image_folder:
                capture_filename = f"{control.ControlType}_{image_idx}.png"
                img_path = str(image_folder / capture_filename)
                try:
                    control.CaptureToImage(img_path)
                except Exception as exc:  # pylint: disable=broad-except
                    self.logger.warning(
                        "Couldn't capture into %r due to: %s", img_path, exc
                    )
                else:
                    control_str += f" [{capture_filename}]"
            space = " " * depth * 4
            child_pos = brothers_count[hash(control)] - children_remaining
            control_log(f"{space}{depth + 1}-{child_pos}. ${control_str}")
            if return_structure:
                element = WindowsElement(control, locator)
                structure.setdefault(depth + 1, []).append(element)
            image_idx += 1

        return structure if return_structure else None

    @keyword
    def get_attribute(self, locator: Locator, attribute: str) -> str:
        """Get attribute value of the element defined by the locator.

        :param locator: string locator or Control element
        :param attribute: name of the attribute to get
        :return: value of attribute

        Example:

        .. code-block:: robotframework

            ${id}=   Get Attribute  type:Edit name:firstname   AutomationId
        """
        # TODO. Add examples
        element = self.ctx.get_element(locator)
        attr = hasattr(element.item, attribute)
        if not attr:
            raise ActionNotPossible(
                f"Element found with {locator!r} does not have {attribute!r} attribute"
            )
        if callable(attr):
            raise ActionNotPossible(
                f"Can't access attribute {attribute!r} of element {element!r}"
            )
        return str(getattr(element.item, attribute))

    @keyword
    def list_attributes(self, locator: Locator) -> List:
        """List all element attributes.

        :param locator: string locator or Control element
        :return: list of element attributes (strings)
        """
        element = self.ctx.get_element(locator)
        element_attributes = [e for e in dir(element.item) if not e.startswith("_")]
        attributes = []

        for attr_name in element_attributes:
            attr = getattr(element.item, attr_name)
            if not inspect.ismethod(attr):
                attributes.append(attr_name)
        return attributes
