UP = 1
DOWN = 2
FLOOR_COUNT = 6


class ElevatorLogic(object):
    """
    An incorrect implementation. Can you make it pass all the tests?

    Fix the methods below to implement the correct logic for elevators.
    The tests are integrated into `README.md`. To run the tests:
    $ python -m doctest -v README.md

    To learn when each method is called, read its docstring.
    To interact with the world, you can get the current floor from the
    `current_floor` property of the `callbacks` object, and you can move the
    elevator by setting the `motor_direction` property. See below for how this is done.
    """

    def __init__(self):
        # Feel free to add any instance variables you want.
        self.callbacks = None

        self.service_direction = None
        self.is_ready_to_switch_direction = False
        self.pick_up_floors_by_direction = {UP: [], DOWN: []}
        self.drop_off_floors = []
        self.is_drop_off_request_selection_pending = False

    def on_called(self, floor, direction):
        """
        This is called when somebody presses the up or down button to call the elevator.
        This could happen at any time, whether or not the elevator is moving.
        The elevator could be requested at any floor at any time, going in either direction.

        floor: the floor that the elevator is being called to
        direction: the direction the caller wants to go, up or down
        """
        # handle invalid input
        if (self._is_pick_up_requested_on_floor(floor, direction) or
                (floor == 1 and direction == DOWN) or
                (floor == FLOOR_COUNT and direction == UP)):
                    return

        # if the elevator is idle lock in this direction immediately
        if self._is_idle():
            self.service_direction = self._get_requested_direction(floor)

        self._add_to_pick_up_floors(direction, floor)

    def on_floor_selected(self, floor):
        """
        This is called when somebody on the elevator chooses a floor.
        This could happen at any time, whether or not the elevator is moving.
        Any floor could be requested at any time.

        floor: the floor that was requested
        """
        # handle invalid input
        if floor in self.drop_off_floors:
            return

        # get the direction that this request is for
        direction_of_request = self._get_requested_direction(floor)

        # if no service direction is set then lock in requested direction
        if self.service_direction is None:
            self.service_direction = direction_of_request
            self.drop_off_floors.append(floor)
        else:
            # if a switch of direction is allowed and this request is in the new direction then
            # the switch can occur
            if self.is_ready_to_switch_direction and direction_of_request == self._get_opposite_service_direction():
                self.service_direction = self._get_opposite_service_direction()
                self.drop_off_floors.append(floor)
                self.is_ready_to_switch_direction = False

            # only accept drop off requests to floors that are ahead in the current service direction
            elif not self.is_ready_to_switch_direction and direction_of_request == self.service_direction:
                self.drop_off_floors.append(floor)

    def on_floor_changed(self):
        """
        This lets you know that the elevator has moved one floor up or down.
        You should decide whether or not you want to stop the elevator.
        """
        # Stop the elevator for the following conditions:
        #   - if this floor is a drop off destination
        #   - if this floor has a pickup request for the current service direction
        #   - if this floor has a pickup request for the opposite service direction, and
        #       the elevator has no more service requests in the current service direction

        # check if this floor is a drop off destination
        if self._is_current_floor_drop_off_destination():
            # stop here for drop off
            self.callbacks.motor_direction = None
            self._remove_drop_off_request_for_this_floor()

        # check if the elevator's current location and direction matches a service request
        if self._is_pick_up_requested_on_this_floor(self.service_direction):
            # stop here for pick up
            self.callbacks.motor_direction = None

        # check if the elevator has no more requests ahead in the current service direction and can stop
        # here to pick up a request to go in the opposite direction
        elif not self._are_more_drop_off_or_pickup_requests_ahead(self.service_direction):
            if self._is_pick_up_requested_on_this_floor(self._get_opposite_service_direction()):
                # stop here for pick up
                self.callbacks.motor_direction = None
                self.is_ready_to_switch_direction = True

        # ensure that we do not move outside of the floor bounds
        assert not (self.callbacks.current_floor == 1 and self.callbacks.motor_direction == DOWN)
        assert not (self.callbacks.current_floor == FLOOR_COUNT and self.callbacks.motor_direction == UP)

    def on_ready(self):
        """
        This is called when the elevator is ready to go.
        Maybe passengers have embarked and disembarked. The doors are closed,
        time to actually move, if necessary.
        """
        # If there are no outstanding service requests the motor direction is set to none and the elevator
        # will entire idle mode.
        # If there are  more service requests in the current service direction then the motor must continue in this
        # direction.
        # If there are instead request in the other direction then the motor should be set to this other direction

        # Check if the elevator should continue in its current service direction
        if self._are_more_drop_off_or_pickup_requests_ahead(self.service_direction):
            self.callbacks.motor_direction = self.service_direction
            # remove the pick up request as it has been handled
            if self._is_pick_up_requested_on_this_floor(self.service_direction):
                self._remove_pick_up_requested_on_this_floor(self.service_direction)

        # Check if the elevator only has a pick up request in the service direction
        elif self._is_pick_up_requested_on_this_floor(self.service_direction):
            # Check if there is a pick up request in the opposite direction
            if self._is_pick_up_requested_on_this_floor(self._get_opposite_service_direction()):
                # don't move as we don't know what the destination floor is
                self.callbacks.motor_direction = None
                # remove the service request as it has been serviced
                self._remove_pick_up_requested_on_this_floor(self.service_direction)
                # switch service direction
                self.service_direction = self._get_opposite_service_direction()

            # Check if there are service requests in the opposite direction
            elif self._are_more_drop_off_or_pickup_requests_ahead(self._get_opposite_service_direction()):
                self.service_direction = self._get_opposite_service_direction()
                self.callbacks.motor_direction = self.service_direction
            else:
                # remove the service request as it has been serviced
                self._remove_pick_up_requested_on_this_floor(self.service_direction)
                # don't move as we don't know what the destination floor is
                self.service_direction = None
                self.callbacks.motor_direction = None

        # Check if there are service requests in the opposite direction
        elif self._are_more_drop_off_or_pickup_requests_ahead(self._get_opposite_service_direction()):
            # switch direction and move
            self.service_direction = self._get_opposite_service_direction()
            self.callbacks.motor_direction = self.service_direction

            # remove the pick up request as it has been handled
            if self._is_pick_up_requested_on_this_floor(self.service_direction):
                self._remove_pick_up_requested_on_this_floor(self.service_direction)

        # check if there is only a pick up request and no drop off yet
        elif self._is_pick_up_requested_on_this_floor(self._get_opposite_service_direction()):
            # switch direction but don't move
            self.service_direction = self._get_opposite_service_direction()
            self.callbacks.motor_direction = None

            # remove the pick up request as it has been handled
            if self._is_pick_up_requested_on_this_floor(self.service_direction):
                self._remove_pick_up_requested_on_this_floor(self.service_direction)

        else:
            # no more service requests so stop and go idle
            self.service_direction = None
            self.callbacks.motor_direction = None

        self.is_ready_to_switch_direction = False

        # ensure that we do not move outside of the floor bounds
        assert not (self.callbacks.current_floor == 1 and self.callbacks.motor_direction == DOWN)
        assert not (self.callbacks.current_floor == FLOOR_COUNT and self.callbacks.motor_direction == UP)

    def _get_requested_direction(self, floor):
        if floor > self.callbacks.current_floor:
            return UP
        elif floor < self.callbacks.current_floor:
            return DOWN
        else:
            return None

    def _is_idle(self):
        return (len(self.drop_off_floors) == 0 and
                len(self.pick_up_floors_by_direction[UP]) == 0 and
                len(self.pick_up_floors_by_direction[DOWN]) == 0)

    def _are_more_drop_off_or_pickup_requests_ahead(self, direction):
        return self._are_more_drop_off_requests_ahead(direction) or self._are_more_pick_up_requests_ahead(direction)

    def _is_current_floor_drop_off_destination(self):
        return self.callbacks.current_floor in self.drop_off_floors

    def _add_to_pick_up_floors(self, direction, floor):
        self.pick_up_floors_by_direction[direction].append(floor)

    def _is_pick_up_requested_on_floor(self, floor, direction):
        if direction is None:
            return False

        return floor in self.pick_up_floors_by_direction[direction]

    def _is_pick_up_requested_on_this_floor(self, direction):
        return self._is_pick_up_requested_on_floor(self.callbacks.current_floor, direction)

    def _remove_pick_up_requested_on_this_floor(self, direction):
        self.pick_up_floors_by_direction[direction].remove(self.callbacks.current_floor)

    def _are_more_drop_off_requests_ahead(self, direction):
        if direction is None:
            return False

        if direction == UP:
            return len(self.drop_off_floors) > 0 and max(self.drop_off_floors) > self.callbacks.current_floor
        else:
            return len(self.drop_off_floors) > 0 and min(self.drop_off_floors) < self.callbacks.current_floor

    def _remove_drop_off_request_for_this_floor(self):
        self.drop_off_floors.remove(self.callbacks.current_floor)

    def _are_more_pick_up_requests_ahead(self, direction):
        if direction is None:
            return False

        if direction == UP:
            return (
                (
                    # going up there is a floor ahead with a UP request
                    len(self.pick_up_floors_by_direction[UP]) > 0 and
                    max(self.pick_up_floors_by_direction[UP]) > self.callbacks.current_floor
                ) or
                (
                    # going up there is a floor ahead with a DOWN request
                    len(self.pick_up_floors_by_direction[DOWN]) > 0 and
                    max(self.pick_up_floors_by_direction[DOWN]) > self.callbacks.current_floor
                )
            )
        else:
            return (
                (
                    # going down there is a floor ahead with a UP request
                    len(self.pick_up_floors_by_direction[UP]) > 0 and
                    min(self.pick_up_floors_by_direction[UP]) < self.callbacks.current_floor
                ) or
                (
                    # going down there is a floor ahead with a DOWN request
                    len(self.pick_up_floors_by_direction[DOWN]) > 0 and
                    min(self.pick_up_floors_by_direction[DOWN]) < self.callbacks.current_floor
                )
            )

    def _get_opposite_service_direction(self):
        if self.service_direction == UP:
            return DOWN
        else:
            return UP
