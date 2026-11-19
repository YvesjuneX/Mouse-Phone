export const remoteCommands = {
  move: (dx: number, dy: number) => ({ type: 'move', dx, dy }),
  moveEnd: () => ({ type: 'move_end' }),
  click: () => ({ type: 'click', button: 'left' }),
  scroll: (amount: number) => ({ type: 'scroll', amount }),
  media: (action: string) => ({ type: 'media', action }),
};
